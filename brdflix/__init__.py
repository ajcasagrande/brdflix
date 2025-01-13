#!/usr/bin/python
import os
import sys
import shutil
from jinja2 import Environment, FileSystemLoader
import re
import urllib
import socket
import random

def get_external_ip():
    html = urllib.urlopen("https://<TODO>.com/public_ip.php").read()
    grab = re.findall('\d{2,3}.\d{2,3}.\d{2,3}.\d{2,3}', html)
    address = grab[0]
    return address

def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8",80))
    ip = s.getsockname()[0]
    s.close()
    return ip

# Data directories
PROG_DIR = os.getcwd()
DATA_DIR = os.path.join(PROG_DIR, 'data')
CSS_DIR = os.path.join(PROG_DIR, 'data/css')
JS_DIR = os.path.join(PROG_DIR, 'data/js')
IMAGES_DIR = os.path.join(PROG_DIR, 'data/images')
TMPL_DIR = os.path.join(PROG_DIR, 'data/interfaces/default')
JINJA_TEMPLATES_DIR = os.path.join(PROG_DIR, 'data/templates')

jinja_env = Environment(loader=FileSystemLoader(JINJA_TEMPLATES_DIR))

LOG_DIR = os.path.join(PROG_DIR, 'logs')
CERTS_DIR = os.path.join(PROG_DIR, 'certs')
SETTINGS_DIR = os.path.join(PROG_DIR, 'settings')
TRANSCODE_DIR = os.path.join(PROG_DIR, 'transcode')

DATABASE_FILENAME = os.path.join(PROG_DIR, 'brdflix.db')

CHERRYPY_LOG = os.path.join(LOG_DIR, 'cherrypy.log')
LOG = os.path.join(LOG_DIR, 'brdflix.log')
LOG_OLD = os.path.join(LOG_DIR, 'brdflix.old.log')

try:
    # Get the external ip for checking if the user is local or not
    LAN_IP = get_lan_ip()
    print "LAN IP:", LAN_IP
except:
    LAN_IP = ""

IS_BETA = 'beta' in PROG_DIR
if IS_BETA:
    print "RUNNING IN BETA MODE!"
else:
    # TODO: This works with pythonw.exe, but it is very slow to flush the file
    # Log output to file
    if os.path.isfile(LOG):
        shutil.copy(LOG, LOG_OLD)
    sys.stdout = open(LOG, 'w')

# Cookies
LOGIN_COOKIE = 'brdflix_login'
QUALITY_COOKIE = 'brdflix_quality'
AUTOPLAY_COOKIE = 'brdflix_autoplay'
VOLUME_COOKIE = 'brdflix_vol'

import webtools
webtools.setup()

import settings
settings.load_all()

EXTERNAL_IP = ""
retry = 0
while retry < settings.GLOBAL.external_ip_retries and EXTERNAL_IP == "":
    try:
        # Get the external ip for checking if the user is local or not
        print "Checking external ip..."
        EXTERNAL_IP = get_external_ip()
        print "EXTERNAL IP:", EXTERNAL_IP
    except:
        retry += 1
        EXTERNAL_IP = ""
        print "Error detecting external IP!"

NEW_EPS_INTERVAL = 60 * settings.EMAIL.new_check_mins

PORT = settings.GLOBAL.port if not IS_BETA else settings.GLOBAL.beta_port

import jinja_filters

# A random number to designate the current running instance,
# to be used for things like CSS so the browser can only cache per
# run instance
RUN_ID = random.randint(100000000, 999999999)
print "RUN_ID:", RUN_ID

AUTO_BASE_URL = settings.GLOBAL.beta_base_url if IS_BETA else settings.GLOBAL.base_url

print "LOADED __INIT__.PY FOR BRDFLIX"
