import MySQLdb
from MySQLdb.cursors import DictCursor
from pprint import pprint
import urllib
from datetime import datetime

from base_providers import *
from meta_types import *
from brdflix.datatypes import *
from brdflix.db_mysql import ConnectionInfo, MySqlHelper

class XBMCSQLProvider(TVProvider, MovieProvider, FileProvider):
    _host = "<TODO>"
    _port = 7010
    _user = "<TODO>"
    _password = "<TODO>"
    _db_name = "xbmc_video75"

    def __init__(self):
        s = XBMCSQLProvider
        self._connect_info = ConnectionInfo(s._host, s._port, s._user, s._password, s._db_name)
        self.db = MySqlHelper(self._connect_info)

    def get_episodes(self, id_show, season=-1):
        query = '''
        select * from episodeview
        where idShow = %s and c12 = %s '''
        rows = self.db.fetch_all(query, (id_show, season))
        objs = DatabaseObject()._create_objects(rows, True)
        eps = []
        for obj in objs:
            ep = _parse_episodeview(obj)
            eps.append(ep)
        return eps

    def get_episode_info(self, id_episode):
        query = '''
        select * from episodeview
        where idEpisode = %s '''
        rows = self.db.fetch_one(query, (id_episode,))
        obj = DatabaseObject()._create_object(rows, True)
        ep = _parse_episodeview(obj)
        return ep

    def get_recent_episodes(self):
        query = '''
        select * from episodeview
        order by dateAdded desc
        limit 50 '''
        rows = self.db.fetch_all(query, None)
        objs = DatabaseObject()._create_objects(rows, True)
        eps = []
        for obj in objs:
            ep = _parse_episodeview(obj)
            eps.append(ep)
        return eps

    def get_seasons(self, id_show):
        return None

    def get_shows(self):
        return None

    def get_show_info(self, id_show):
        return None

    def get_show_poster(self, id_show):
        return None

    def get_show_tvdb_id(self, id_show):
        return None

def _parse_episodeview(obj):
    ep = BaseEpisode()
    ep.idShow = obj.idShow
    ep.id = obj.idEpisode
    ep.season = int(obj.c12)
    ep.episode = int(obj.c13)
    ep.fname = obj.strFileName
    ep.file = obj.c18
    ep.showName = obj.strTitle
    ep.epName = obj.c00
    ep.summary = obj.c01
    ep.watched = obj.playCount is not None and obj.playCount > 0
    ep.resume = ""
    ep.thumb_path = "image://" + urllib.quote(ep.file[:ep.file.rfind('.')] + ".tbn").replace('.', '%2e').replace('/', '%2f')
    ep.firstaired = obj.c05
    ep.dateadded = datetime.now() #obj.dateAdded
    return ep
