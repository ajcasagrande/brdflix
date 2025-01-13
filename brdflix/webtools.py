import cherrypy
import time
from pprint import pprint
from datetime import datetime
import sys
import httpagentparser
import base64
import re
import urllib

from db_mysql import DEFAULT as db
from datatypes import *
import transcode
import mailer
from helpers import *

def transcode_end():
    """
    This function should get called whenever the connection
    is completed or closed by the user.
    """
    stream_obj = None
    if hasattr(cherrypy.request, 'stream_obj'):
        stream_obj = cherrypy.request.stream_obj
        stream_obj.end_time = datetime.now()
    if hasattr(cherrypy.request, 'transcode_process'):
        p = cherrypy.request.transcode_process
        if stream_obj is None:
            stream_obj = p.stream_obj
        # Wait for process to finish
        time.sleep(0.2)
        if p.process.poll() is None:
            print "KILLING ffmpeg64 :", p.guid
            p.process.terminate()
        if p in transcode.ACTIVE_PROCESSES:
            transcode.ACTIVE_PROCESSES.remove(p)
        if stream_obj:
            stream_obj.transfer_size = p.transfer_size
            dur = (stream_obj.end_time - stream_obj.start_time).total_seconds()
            MB = p.transfer_size / 1048576.0
            mbps = MB / dur * 8.0
            if p.active_part and not p.active_part.id:
                p.active_part.end_ms = int(round(time.time() * 1000))
                p.active_part.end_bytes = p.transfer_size
                p.active_part.insert()
            print "Final transfer: {0} MB, {1} seconds, {2} Mbps".format(MB, dur, mbps)
        # delete the process to clean up handles
        del p.process
    if stream_obj and stream_obj.id:
        stream_obj.update(['start_time', 'end_time', 'transfer_size'])

def process_request(link_hosts=True, get_previous=True):
    """
    Process a request into a request object
    """
    # If behind a reverse proxy
    forward = cherrypy.request.headers.get('X-Forwarded-For', None)
    if forward is not None and re.search(r'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+', forward) is not None:
        cherrypy.request.remote.ip_orig = cherrypy.request.remote.ip
        cherrypy.request.remote.ip = forward

    cherrypy.request.full_ip = cherrypy.request.remote.ip
    # if the ip is actually CSV
    if ',' in cherrypy.request.remote.ip:
        cherrypy.request.remote.ip = cherrypy.request.remote.ip[cherrypy.request.remote.ip.rfind(',')+1:].strip()

    if link_hosts:
        cherrypy.request.known_host = KnownHost().from_ip(cherrypy.request.remote.ip)

    rq = cherrypy.request.request_line
    rq = rq[rq.find(' ')+1:]
    rq = rq[:rq.find(' HTTP/')]
    req = Request(method=cherrypy.request.method, request=rq, ip_address=cherrypy.request.remote.ip)
    req.user_id = cherrypy.request.user.id if hasattr(cherrypy.request, "user") else None
    req.user_agent = cherrypy.request.headers.get('User-Agent', None)

    host = cherrypy.request.base
    if '/' in host:
        host = host[host.rfind('/')+1:]
    if ':' in host:
        host = host[:host.rfind(':')]
    # host will be something like: stream.<TODO>.com, home.<TODO>.com, <TODO>
    cherrypy.request.is_local = False
    if cherrypy.request.remote.ip == brdflix.EXTERNAL_IP or host == brdflix.LAN_IP:
        cherrypy.request.is_local = True

    cherrypy.request.request_obj = req

#    ua = httpagentparser.simple_detect(req.user_agent)
#    print ua

    # Prevent blocked hosts from accessing site
    if cherrypy.request.known_host is not None and cherrypy.request.known_host.blocked:
        log_unauthorized_request()
        raise cherrypy.HTTPError(403)
    
    if get_previous and req.user_id is not None:
        cherrypy.request.last_req = Request().query_one(user_id=req.user_id, request=req.request, method=req.method, order_by='`timestamp` desc')
    else:
        cherrypy.request.last_req = None

def log_unauthorized_request():
    br = BlockedRequest(_req_obj=cherrypy.request.request_obj)
    br.base = cherrypy.request.base
    br.full_ip = cherrypy.request.full_ip
    br.known_host_id = cherrypy.request.known_host.id if cherrypy.request.known_host else None
    br.http_code = 403
    br.referer = cherrypy.request.headers.get('Referer', None)
    br.insert()

def log_request(database=True, console=True):
    """
    Log a request to the database and or the console.
    """
    if cherrypy.request.request_obj is not None:
        if database:
            cherrypy.request.request_obj.insert()

        if console:
            print "[{0}][{1}][{2}][{3}] {4} {5}".format(
                time.strftime("%Y-%m-%d", time.localtime()),
                time.strftime("%I:%M:%S %p", time.localtime()).lstrip('0'),
                cherrypy.request.remote.ip if cherrypy.request.known_host is None else cherrypy.request.known_host.name,
                cherrypy.request.user.username if hasattr(cherrypy.request, "user") else "N/A",
                cherrypy.request.method,
                cherrypy.request.request_obj.request)

def login_required(admin_only=False):
    """
    Attempt to login and if fail, redirrect to login page
    """
    if not _attempt_login():
        rq = cherrypy.request.request_line
        rq = rq[rq.find(' ')+1:]
        rq = rq[:rq.find(' HTTP/')]
        raise cherrypy.HTTPRedirect("/user/login/?referer={0}".format(urllib.quote(rq)))
    elif admin_only and not cherrypy.request.user.group.admin_rights:
        print "ERROR! User {0} attempted to perform an admin function!".format(cherrypy.request.user.username)
        raise cherrypy.HTTPRedirect("/admin/error/")

def _attempt_login():
    logged_in = False
    cookie = get_cookie(brdflix.LOGIN_COOKIE)
    if cookie is not None:
        logged_in = _attempt_login_string(cookie.value)
    return logged_in

def _attempt_login_string(login_info):
    tokens = login_info.split('$$')
    username = tokens[0]
    sha_password = tokens[1]
    user = User().from_name(username)
    cherrypy.request.user = user
    logged_in = user is not None and user.password == sha_password
    if logged_in:
        if user.enabled:
            # set last access and ip info and send to database
            user.last_access = datetime.now()
            user.last_ip = cherrypy.request.remote.ip
            user.update(['last_access', 'last_ip'])
        else:
            logged_in = False
    return logged_in

def login_from_zl(zl, raise_errors):
    logged_in = _attempt_login_string(base64.b64decode(zl))
    if logged_in:
        # Update the user_id of the request object in the database
        if hasattr(cherrypy.request, "request_obj"):
            cherrypy.request.request_obj.user_id = cherrypy.request.user.id
            cherrypy.request.request_obj.update(["user_id"])
    elif raise_errors:
        # Raises not authorized exception
        raise cherrypy.HTTPError(401)
    return logged_in

def setup():
    """
    Custom tools for CherryPy server.
    Note please keep these in order of when they should occur chronologically.
    See: http://docs.cherrypy.org/stable/progguide/extending/customtools.html
    """
    cherrypy.tools.process_request = cherrypy.Tool('before_request_body', process_request)
    cherrypy.tools.log_request = cherrypy.Tool('before_handler', log_request)
    cherrypy.tools.login_required = cherrypy.Tool('on_start_resource', login_required)
    cherrypy.tools.transcode_end = cherrypy.Tool('on_end_request', transcode_end)
    print "WEBTOOLS SETUP"
