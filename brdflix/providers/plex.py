import urllib2
from datetime import datetime
from BeautifulSoup import BeautifulSoup

from base_providers import *
from meta_types import *
from brdflix.datatypes import *

class PlexProvider(TVProvider, MovieProvider, FileProvider):
    def __init__(self):
        self._host = "<TODO>"
        self._port = 32400
        self._protocol = "http"
        self._tv_id = -1
        self._movies_id = -1

    def _get_base_url(self):
        return "{0}://{1}:{2}".format(self._protocol, self._host, self._port)

    def _get_api_url(self, sub_url, **kwargs):
        url = "{0}{1}".format(self._get_base_url(), sub_url)
        i = 0
        for key in kwargs:
            if i == 0:
                url = "{0}?{1}={2}".format(url, key, kwargs[key])
            else:
                url = "{0}&{1}={2}".format(url, key, kwargs[key])
            i += 1
        return url

    def _get_movies_path_id(self):
        if self._movies_id != -1:
            return self._movies_id
        else:
            url = self._get_api_url('/library/sections')
            xml = get_xml(url)
            bs = BeautifulSoup(xml)
            for dir in bs.findAll('directory'):
                # TODO: HACK:
                if dir['type'] == 'movie' and dir['title'] == "Movies":
                    self._movies_id = dir['key']
                    break
        return self._movies_id

    def _get_tv_path_id(self):
        if self._tv_id != -1:
            return self._tv_id
        else:
            url = self._get_api_url('/library/sections')
            xml = get_xml(url)
            bs = BeautifulSoup(xml)
            for dir in bs.findAll('directory'):
                # TODO: HACK:
                if dir['type'] == 'show' and dir['title'] == "TV Shows":
                    self._tv_id = dir['key']
                    break
        return self._tv_id

    def get_episodes(self, id_show, season=-1):
        return None

    def get_episode_info(self, id_episode):
        return None

    def get_recent_episodes(self):
        return None

    def get_seasons(self, id_show):
        return None

    def get_shows(self):
        url = self._get_api_url('/library/sections/{0}/all'.format(self._get_tv_path_id()))
        xml = get_xml(url)
        bs = BeautifulSoup(xml)
        shows = []
        for dir in bs.findAll('directory', type='show'):
            show = BaseShow()
            show.id = try_get_int(dir, 'ratingkey')
            show.name = try_get(dir, 'title')
            show.totalEps = try_get_int(dir, 'leafcount')
            show.watchedEps = try_get_int(dir, 'viewedleafcount')
            show.seasons = 0
            show.thumb_path = try_get(dir, 'thumb')
            show.plot = try_get(dir, 'summary')
            show.mpaa = try_get(dir, 'contentrating')
            shows.append(show)
        return shows


    def get_show_info(self, id_show):
        return None

    def get_show_poster(self, id_show):
        return None

    def get_show_tvdb_id(self, id_show):
        return None


def get_xml(url):
    return urllib2.urlopen(url).read()

def try_get(obj, key, default=""):
    try:
        return obj[key]
    except:
        return default

def try_get_int(obj, key, default=-1):
    try:
        return int(obj[key])
    except:
        return default
