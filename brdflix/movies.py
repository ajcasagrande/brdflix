import cherrypy
import urllib

from helpers import *
from decorators import *
from db_mysql import DEFAULT as db
from datatypes import *
import brdflix
import xbmc

class MovieInterface:
    _cp_config = { 'tools.log_request.on': True,
                   'tools.login_required.on': True }

    @cherrypy.expose
    def index(self, show_watched="True", sort_method="label", ascending="True", ignorearticle="True", genres=None):
        t, j = get_jinja_template("movies.html")
        j.movies = xbmc.getMovies(ascending, sort_method, ignorearticle)
        if genres is not None:
            j.movies = xbmc.filterMoviesByGenres(j.movies, genres.split(','))
        j.all_genres = xbmc.getAllUniqueGenres(j.movies)
        j.show_watched = show_watched == "True"
        j.watched_status = cherrypy.request.user.watched_status
        return t.render(j.kwargs())

    @cherrypy.expose
    def recent(self, show_watched="True"):
        t, j = get_jinja_template("movies.html")
        j.movies = xbmc.getRecentMovies()
        j.all_genres = xbmc.getAllUniqueGenres(j.movies)
        j.show_watched = show_watched == "True"
        j.watched_status = cherrypy.request.user.watched_status
        return t.render(j.kwargs())

    @cherrypy.expose
    def groups(self):
        t = get_cheetah_template("movieGroups.tmpl")
        t.movies = xbmc.getMovies("True", "label", "True")
        t.all_genres = xbmc.getAllUniqueGenres(t.movies)
        t.show_watched = True
        t.watched_status = cherrypy.request.user.watched_status
        
        grps = {}
        for m in t.movies:
            if m.year >= 2000:
                key = m.year
            else:
                key = 1900 + (int((m.year - 1900) / 10) * 10)
            if not key in grps:
                grps[key] = []
            grps[key].append(m)

        t.grps = grps
        
        return munge(t)  
        
    @cherrypy.expose
    def info(self, idMovie):
        t, j = get_jinja_template('movie_info.html')
        j.movie = xbmc.getMovieInfo(idMovie)
        j.watched_status = cherrypy.request.user.watched_status
        print j.movie.name
        j.search = urllib.quote(j.movie.name)
        return t.render(j.kwargs())
