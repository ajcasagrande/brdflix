import os
import time
#from cheetah.Template import Template
from datetime import date, datetime, timedelta
import cherrypy
import re
import urllib
import json
import decimal
import re

import brdflix
import sickbeard
import settings
import datatypes

class JinjaArgs(object):
    def __init__(self):
        self.user = None
        self.request_obj = None
        self.last_req = None

        self.brdflix = brdflix
        self.sickbeard = sickbeard
        self.settings = settings

    def kwargs(self):
        return self.__dict__

    def add_all(self, kwargs, regex=None):
        for key, val in kwargs.items():
            if regex is None or re.search(regex, key) is not None:
                self.__dict__[key] = val

def get_cookie(key):
    """
    Returns a cookie for the key, or None if it doesn't exist
    """
    try:
        return cherrypy.request.cookie[key]
    except KeyError:
        return None

def set_cookie(key, value, path='/', expire_days=30, domain=None):
    """
    Sets a cookie's value for the specified path and expire days
    If path is None, don't set path.
    If expire_days is None, expires not set.
    """
    cherrypy.response.cookie[key] = value
    if path is not None:
        cherrypy.response.cookie[key]['path'] = path
    if expire_days is not None:
        cherrypy.response.cookie[key]['expires'] = expires_timestamp(days=expire_days)
    if domain is not None:
        cherrypy.response.cookie[key]['domain'] = domain

def clear_cookie(key, path='/', domain=None):
    """
    Clear a cookie's value
    """
    cherrypy.response.cookie[key] = ''
    if path is not None:
        cherrypy.response.cookie[key]['path'] = path
    if domain is not None:
        cherrypy.response.cookie[key]['domain'] = domain
    cherrypy.response.cookie[key]['expires'] = 0

def munge(string):
    return unicode(string).encode('utf-8', 'xmlcharrefreplace')    

#def get_cheetah_template(name):
#    """
#    Load a cheetah template and fill up general variables
#    """
#    t = Template(open(os.path.join(brdflix.TMPL_DIR, name)).read())
#    # Auto fill out standard variables
#    t.user = getattr(cherrypy.request, 'user', None)
#    t.request_obj = getattr(cherrypy.request, 'request_obj', None)
#    t.last_req = getattr(cherrypy.request, 'last_req', None)
#    return t

def get_jinja_template(name):
    """
    Load a jinja2 template and fill up general variables
    """
    t = brdflix.jinja_env.get_template(name)
    j = JinjaArgs()
    j.user = getattr(cherrypy.request, 'user', None)
    j.request_obj = getattr(cherrypy.request, 'request_obj', None)
    j.last_req = getattr(cherrypy.request, 'last_req', None)
    j.RUN_ID = brdflix.RUN_ID
    j.xbmc_servers = datatypes.XBMCServer().query_all()
    return t, j

def gmtime_for_datetime(dt):
    """
    Pass in a datetime object, and get back time.gmtime
    """
    return time.gmtime(time.mktime(time.strptime(dt.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"))) if dt is not None else None

def gmtime_for_str(str_date):
    """
    Pass in a datetime string, and get back time.gmtime
    """
    return time.gmtime(time.mktime(time.strptime(str_date, "%a, %d-%b-%Y %H:%M:%S GMT"))) if str_date is not None else None

def expires_timestamp(days=None, hours=None, minutes=None, seconds=None):
    """
    Get an expires header timestamp for the specified time from now
    """
    expires = time.time()
    if days:
        expires += days * 3600 * 24
    if hours:
        expires += hours * 3600
    if minutes:
        expires += minutes * 60
    if seconds:
        expires += seconds
    return time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", time.gmtime(expires))

def gmt_timestamp_for_datetime(dt):
    """
    Pass in a datetime object, and get back a gmt timestamp
    for use in cookies and headers.
    """
    if dt is None:
        return None
    return time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", gmtime_for_datetime(dt))

def get_stream_host():
    return 'http://{0}:{1}'.format(brdflix.LAN_IP if cherrypy.request.is_local else brdflix.EXTERNAL_IP, brdflix.PORT)

def round_to_even(num):
    return int(num / 2) * 2

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

class ThumbSegement(object):
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.index = -1

    @property
    def mid_time(self):
        return self.start_time + ((self.end_time - self.start_time) / 2.0)
