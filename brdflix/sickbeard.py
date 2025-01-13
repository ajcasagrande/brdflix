import cherrypy
import os
import urllib2
import json

import brdflix
from decorators import *
from helpers import *
import settings
import xbmc
from datatypes import *

def getApiBaseUrl():
    s = settings.SICKBEARD
    return "{0}/api/{1}/".format(getHtmlBaseUrl(), s.api_key)

def getHtmlBaseUrl(basic_auth=False, external=False):
    s = settings.SICKBEARD
    if basic_auth:
        return "{0}://{1}:{2}@{3}:{4}".format(s.protocol, s.user, s.password, s.internal_host, s.port)
    else:
        return "{0}://{1}:{2}".format(s.protocol, s.internal_host if not external else s.external_host, s.port)
    
def getBasicAuthHtmlBaseUrl(external=False):
    s = settings.SICKBEARD
    return "{0}://{1}:{2}@{3}:{4}".format(s.protocol, s.user, s.password, s.internal_host if not external else s.external_host, s.port)
    
def getApiUrl(cmd, **kwargs):
    url = "{0}?cmd={1}".format(getApiBaseUrl(), cmd)
    for key in kwargs:
        url = "{0}&{1}={2}".format(url, key, kwargs[key])
    return url
    
def getShowDetailsUrl(tvdb_id, basic_auth=False, external=True):
    return "{0}/home/displayShow?show={1}".format(getHtmlBaseUrl(basic_auth, external), tvdb_id)

def show(tvdb_id):
    url = getApiUrl('show', tvdbid=tvdb_id)
    return json.loads(urllib2.urlopen(url).read())

def getJSON(cmd, **kwargs):
    url = "{0}?cmd={1}".format(getApiBaseUrl(), cmd)
    for key in kwargs:
        url = "{0}&{1}={2}".format(url, key, kwargs[key])
    js = urllib2.urlopen(url).read()
    return json.loads(js)

def setEpisodeQualities(tvdb_id, season):
    sb_info = getJSON("show.seasons", tvdbid=tvdb_id, season=season.num)['data']
    for ep in season.eps:
        for key, val in sb_info.items():
            found = False
            if int(ep.episode) == int(key):
                ep.quality = val['quality']
                found = True
                break
#        if not found:
#            # Create a simple missing episode
#            ep = Episode()
#            ep.idShow = season.idShow
#            ep.season = season.num
#            ep.episode = int(key)
#            ep.showName = season.showName
#            ep.missing = True
#            # Still need to work on this, as it is currently adding episodes not yet aired
#            #season.eps.append(ep)

def comingTypeToCSS(type):
    q = "sb_coming "
    if type in ['missed']:
        return q + "sb_missed"
    elif type in ['today']:
        return q + "sb_today"
    elif type in ['soon']:
        return q + "sb_soon"
    elif type in ['later']:
        return q + "sb_later"
    return q

def qualityToCSS(quality):
    q = "quality "
    if quality in ['HD TV', '720p WEB-DL', '720p BluRay']:
        return q + "HD720p"
    elif quality in ['1080p HDTV', '1080p WEB-DL', '1080p BluRay']:
        return q + "HD1080p"
    elif quality in ['RawHD TV']:
        return q + "RawHD"
    elif quality in ['SD TV', 'SD DVD']:
        return q + "SD"
    return q + "Any"

def statusToCSS(status):
    q = "quality "
    if status in ['Continuing']:
        return q + "HD720p"
    elif status in ['Ended']:
        return q + "SD"
    return q + "Any"

def getComingsEps(all=True, missed=True, today=True, soon=True, later=True):
    # all means not just favorites, but every show
    faves_only = not all
    tps = []
    if missed: tps.append("missed")
    if today: tps.append("today")
    if soon: tps.append("soon")
    if later: tps.append("later")
    type = "|".join(tps)
    js = getJSON("future", type=type)
    data = js['data']
    coming = []
    for tp in tps:
        for ep in data[tp]:
            ep['type'] = tp
            coming.append(ep)
    faves = FavoriteShow.get_all_from_user(cherrypy.request.user.id)
    fave_ids = [ fave.tvdb_id for fave in faves ]
    shows = xbmc.getShows()
    eps = []
    for c in coming:
        if not faves_only or c['tvdbid'] in fave_ids:
            for show in shows:
                if int(show.tvdb_id) == int(c['tvdbid']):
                    ep = xbmc.Episode()
                    ep.idShow = show.id
                    ep.season = c['season']
                    ep.episode = c['episode']
                    ep.showName = c['show_name']
                    ep.epName = c['ep_name']
                    ep.summary = c['ep_plot']
                    ep.firstaired = c['airdate']
                    ep.airtime = c['airs']
                    ep.network = c['network']
                    ep.quality = c['quality']
                    ep.show_status = c['show_status']
                    ep.type = c['type']
                    ep.tvdb_id = show.tvdb_id
                    try:
                        dt = datetime.strptime(ep.firstaired, "%Y-%m-%d")
                        now = datetime.now()
                        diff = now - dt
                        ep.days_away = diff.days * -1
                    except:
                        ep.days_away = None
                    eps.append(ep)
                    break
    return eps

class SickBeardInterface:
    _cp_config = { 'tools.login_required.on': True }
    
    @cherrypy.expose
    def index(self, **kwargs):
        return self.api(**kwargs)

    @cherrypy.expose
    def api(self, **kwargs):
        url = getApiBaseUrl()
        if 'cmd' in kwargs.keys():
            url = "{0}?cmd={1}".format(url, kwargs['cmd'])
        for key in kwargs:
            if key != 'cmd':
                url = "{0}&{1}={2}".format(url, key, kwargs[key])
        response = urllib2.urlopen(url)
        data = response.read()
        # Detect the response type and reflect it back to the caller
        response_type = response.info().getheader('Content-Type')
        cherrypy.response.headers['Content-Type'] = response_type
        return data

    @cherrypy.expose
    def banner(self, id):
        return self.api(cmd='show.getbanner', tvdbid=id)

    @cherrypy.expose
    def poster(self, id):
        return self.api(cmd='show.getposter', tvdbid=id)
        