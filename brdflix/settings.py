import ConfigParser
import os

import brdflix

DEFAULT_INI = os.path.join(brdflix.SETTINGS_DIR, 'default.ini')

def load_all():
    global GLOBAL, XBMC, SICKBEARD, COUCHPOTATO, MYSQL, EMAIL
    load_generic(GLOBAL, 'Global')
    load_generic(XBMC, 'XBMC')
    load_generic(SICKBEARD, 'SickBeard')
    load_generic(COUCHPOTATO, 'CouchPotato')
    load_generic(MYSQL, 'MySQL')
    load_generic(EMAIL, 'Email')

def load_generic(obj, section):
    errors = loadSettings(DEFAULT_INI, obj, section)
    if errors != 0:
        print errors, "errors processing settings for", section
    return obj

def loadSettings(fname, obj, section, ignore=['valid']):
    """
    Generically deserializes a settings object
    from a specified ini file based on the predefined
    class variables.

    Returns:
        -1 if could not read file
        0 if no errors
        >0 positive number of errors if there were errors
    """
    errors = -1
    if os.path.isfile(fname):
        errors = 0
        Config = ConfigParser.ConfigParser()
        Config.read(fname)
        for key, val in obj.__dict__.items():
            if not key in ignore:
                try:
                    value = val
                    if type(val) is int:
                        value = Config.getint(section, key)
                    elif type(val) is bool:
                        value = Config.getboolean(section, key)
                    else:
                        value = Config.get(section, key)
                except:
                    errors = errors + 1
                obj.__dict__[key] = value
    obj.__dict__['valid'] = errors == 0
    return errors

class GlobalSettings(object):
    def __init__(self):
        self.port = 0
        self.beta_port = 0
        self.temp_dir = None
        self.image_cache_dir = None
        self.max_image_cache_days = 0
        self.base_url = ""
        self.beta_base_url = ""
        self.external_ip_retries = 0
        self.max_thumb_threads = 10

class XBMCSettings(object):
    def __init__(self):
        self.filename = None
        self.allow_start_process = False
        self.start_wait_seconds = 3
        self.protocol = "http"
        self.internal_host = ""
        self.external_host = ""
        self.port = 0
        self.user = ""
        self.password = ""

class SickBeardSettings(object):
    def __init__(self):
        self.enabled = False
        self.protocol = "http"
        self.internal_host = ""
        self.external_host = ""
        self.port = 0
        self.user = ""
        self.password = ""
        self.api_key = ""
        
class CouchPotatoSettings(object):
    def __init__(self):
        self.enabled = False
        self.protocol = "http"
        self.internal_host = ""
        self.external_host = ""
        self.port = 0
        self.user = ""
        self.password = ""
        self.api_key = ""

class MySQLSettings(object):
    def __init__(self):
        self.host = ""
        self.port = 3306
        self.user = ""
        self.password = ""
        self.db_name = "brdflix"
        self.beta_db_name = "brdflix_beta"

class EmailSettings(object):
    def __init__(self):
        self.enabled = False
        self.email = ""
        self.password = ""
        self.provider = "gmail"
        self.alert_on_500 = True
        self.new_check_mins = 0

GLOBAL = GlobalSettings()
XBMC = XBMCSettings()
SICKBEARD = SickBeardSettings()
COUCHPOTATO = CouchPotatoSettings()
MYSQL = MySQLSettings()
EMAIL = EmailSettings()
