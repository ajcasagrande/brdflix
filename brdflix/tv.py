import cherrypy
import json
from datetime import date, datetime, timedelta

from helpers import *
from decorators import *
from db_mysql import DEFAULT as db
from datatypes import *
import brdflix
import xbmc
import sickbeard
from brdflix.providers import XBMCProvider, XBMCSQLProvider, PlexProvider
from missing import *

class TVInterface:
    _cp_config = { 'tools.log_request.on': True,
                   'tools.login_required.on': True }

    def __init__(self):
        self.provider = PlexProvider()

    @cherrypy.expose
    def index(self, show_watched="True", sort_method="label", ascending="True", ignorearticle="True"):
        t, j = get_jinja_template("tv.html")
        j.shows = xbmc.getShows(ascending, sort_method, ignorearticle)
        #j.shows = self.provider.get_shows()
        j.show_watched = show_watched == "True"
        j.watched_status = cherrypy.request.user.watched_status
        j.all_genres = xbmc.getAllUniqueGenres(j.shows)
        return t.render(j.kwargs())
        
    @cherrypy.expose
    def recent(self, show_watched="True"):
        t, j = get_jinja_template("recent_episodes.html")
        j.eps = xbmc.getRecentEpisodes()
        #j.eps = self.provider.get_recent_episodes()
        j.show_watched = show_watched == "True"
        j.watched_status = cherrypy.request.user.watched_status
        return t.render(j.kwargs())

    @cherrypy.expose
    def info(self, id, s=-1):
        if cherrypy.request.last_req is not None:
            print "Last Access:", cherrypy.request.last_req.timestamp
        
        t, j = get_jinja_template("tv_info.html")
        j.idShow = id
        j.show = xbmc.getShowInfo(id)
        j.seasons = xbmc.getSeasons(id)
        j.show_watched = True
        j.initial_season = -1
        if int(s) != -1:
            j.initial_season = int(s)
        elif len(j.seasons) == 1:
            j.initial_season = j.seasons[0].num
        for season in j.seasons:
            season.eps = xbmc.getEpisodes(id, season.num)
            sickbeard.setEpisodeQualities(j.show.tvdb_id, season)
            #season.eps = self.provider.get_episodes(id, season.num)
#            for ep in season.eps:
#                if cherrypy.request.last_req is not None and ep.dateadded is not None:
#                    delta = ep.dateadded - cherrypy.request.last_req.timestamp
#                    if delta > timedelta(days=-2):
#                        print 'New:', ep
        j.sb_info = sickbeard.show(j.show.tvdb_id)['data']
        j.show.status = j.sb_info['status']
        if not j.show.status:
            j.show.status = "N/A"
        if j.sb_info['next_ep_airdate']:
            dt = datetime.strptime(j.sb_info['next_ep_airdate'], '%Y-%m-%d')
            j.next_ep_date = date(dt.year, dt.month, dt.day)
            j.next_ep_away = j.next_ep_date - date.today()
        else:
            j.next_ep_date = None
            j.next_ep_away = None

        j.missing = getMissing(j.show, int(s))
        j.sb_src = sickbeard.getHtmlBaseUrl() + '/home/displayShow?show={0}#content'.format(j.show.tvdb_id)
        return t.render(j.kwargs())
