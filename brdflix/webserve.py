import cherrypy
import os
import time
from pprint import pprint, pformat
from cherrypy.lib.static import serve_file
import urllib
import base64
from datetime import datetime, timedelta

from db_mysql import DEFAULT as db
from datatypes import *
from decorators import *
from helpers import *
import brdflix
import xbmc
import sickbeard
import settings
import mailer

class WebInterface:

    _cp_config = { 'tools.log_request.on': False,
                   'tools.login_required.on': False }

    @log_request
    @login_required
    @cherrypy.expose
    def index(self):
#        t = getTemplate("index.tmpl")
#        t.favorite_shows = FavoriteShow.get_all_from_user(t.user.id)
#        return munge(t)
        t, j = get_jinja_template('index.html')
        favorites = FavoriteShow.get_all_from_user(cherrypy.request.user.id)
        j.faves = []
#        for f in favorites:
#            show = xbmc.getShowInfo(f.xbmc_id)
#            faves.append(show)

        # This is a hack because watched count is not working for single shows
        shows = xbmc.getShows()
        for show in shows:
            for f in favorites:
                if f.xbmc_id == show.id:
                    j.faves.append(show)

        query = '''
                select max(timestamp) as latest, resume.*, episode_id
                from resume
                join media on media.id = media_id
                where user_id=%s
                and episode_id is not null
                group by media_id
                order by latest desc
                limit 6
                '''
        rows = db.fetch_all(query, (cherrypy.request.user.id,))
        resume_objs = [ (db.get_generic(Resume(), row, True)) for row in rows ]
        j.resumes = []
        for r in resume_objs:
            if r.episode_id is not None:
                try:
                    j.resumes.append(xbmc.getEpisodeInfo(r.episode_id))
                except:
                    # Possibly the episode no longer exists in the db
                    pass

        query2 = '''
                        select max(timestamp) as latest, resume.*, movie_id
                        from resume
                        join media on media.id = media_id
                        where user_id=%s
                        and movie_id is not null
                        group by media_id
                        order by latest desc
                        limit 10
                        '''
        rows2 = db.fetch_all(query2, (cherrypy.request.user.id,))
        resume_objs2 = [ (db.get_generic(Resume(), row, True)) for row in rows2 ]
        j.movie_resumes = []
        for r in resume_objs2:
            if r.movie_id is not None:
                try:
                    j.movie_resumes.append(xbmc.getMovieInfo(r.movie_id))
                except:
                    # Possibly the movie no longer exists in the db
                    pass

        w_items = WatchlistItem().get_all_from_user(cherrypy.request.user.id)
        j.watchlist = []
        for w in w_items:
            try:
                j.watchlist.append(xbmc.getMovieInfo(w.xbmc_id))
            except:
                # Possibly the movie no longer exists in the db
                pass

        j.sb_base_url = sickbeard.getHtmlBaseUrl(external=True)
        j.coming_eps = sickbeard.getComingsEps(False, True, True, True, False)

        return t.render(j.kwargs())

    @cherrypy.expose
    def derefer_old(self, url, ms=500):
        t, j = get_jinja_template('derefer.html')
        j.url = urllib.unquote(url)
        j.ms = int(ms)
        return t.render(j.kwargs())

    @cherrypy.expose
    def derefer(self, **kwargs):
        key0 = kwargs.keys()[0]
        url = urllib.unquote(key0)
        if url.lower().startswith('http'):
            r = cherrypy.HTTPRedirect(url, 302)
            headers = cherrypy.serving.response.headers
            # Set the referer to the link we are going to
            headers['Referer'] = url
            headers['X-Robots-Tag'] = 'noindex'
            headers['Pragma'] = 'no-cache'
            headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
            raise r
        raise cherrypy.HTTPError(500)

    @cherrypy.expose
    def crossdomain_xml(self):
        cherrypy.response.headers['Content-Type'] = 'text/xml'
        return '''
<?xml version="1.0"?>
<!DOCTYPE cross-domain-policy SYSTEM "http://www.adobe.com/xml/dtds/cross-domain-policy.dtd">
<cross-domain-policy>
   <allow-access-from domain="*" />
</cross-domain-policy>
        '''

    @log_request
    @login_required
    @cherrypy.expose
    def submit_issue(self, **kwargs):
        if 'submit' in kwargs:
            # Handle the form submission
            t, j = get_jinja_template("email/issue_email.html")
            j.media = Media().from_id(kwargs.get('media_id', ''))
            j.details = kwargs['txt_details']
            j.add_all(kwargs, "cb_")
            subject = "BRDFlix Video Issue - {0}".format(j.media.fname)
            body = t.render(j.kwargs())
            mailer.send_to_admin(subject, body, is_html=True)

            # Tell user form is submitted and close the window
            t, j = get_jinja_template("forms/form_submitted.html")
            return t.render(j.kwargs())
        else:
            # Display the form
            t, j = get_jinja_template("forms/submit_issue.html")
            j.media = Media().from_id(kwargs.get('media_id', ''))
            j.embed = kwargs.get('embed', 'False') == 'True'
            return t.render(j.kwargs())

    @log_request
    @login_required
    @cherrypy.expose
    def upcoming(self, all="True", missed="True", today="True", soon="True", later="True"):
        t, j = get_jinja_template("upcoming.html")
        j.sb_base_url = sickbeard.getHtmlBaseUrl(external=True)
        j.coming_eps = sickbeard.getComingsEps(all == "True", missed == "True", today == "True", soon == "True", later == "True")
        j.coming_grps = []
        j.min_days_away = 0
        j.max_days_away = 0
        for ep in j.coming_eps:
            if ep.type != "later":
                if ep.days_away < j.min_days_away:
                    j.min_days_away = ep.days_away
                elif ep.days_away > j.max_days_away:
                    j.max_days_away = ep.days_away
        for i in range(j.min_days_away, j.max_days_away+1):
            grp = ComingGroup()
            for ep in j.coming_eps:
                if ep.days_away == i:
                    grp.eps.append(ep)
            grp.title = format_days_away(i, len(grp.eps))
            grp.days_away = i
            j.coming_grps.append(grp)
        later = ComingGroup()
        later.title = "Later"
        later.days_away = j.max_days_away + 1
        for ep in j.coming_eps:
            if ep.days_away > j.max_days_away:
                later.eps.append(ep)
        if len(later.eps) > 0:
            j.coming_grps.append(later)
        return t.render(j.kwargs())

    @log_request
    @login_required
    @admin_only
    @cherrypy.expose
    def nzb_search(self, show_name, season, episode):
        t, j = get_jinja_template('nzb_search.html')
        j.show_name = show_name
        j.season = int(season)
        j.episode = int(episode)
        return t.render(j.kwargs())

    @log_request
    @login_required
    @cherrypy.expose
    def search(self, q):
        t, j = get_jinja_template('search.html')
        j.movies = []
        j.shows = []
        parts = q.lower().split(' ')
        shows = xbmc.getShows()
        movies = xbmc.getMovies()
        for show in shows:
            match = True
            name = show.name.lower()
            for part in parts:
                if not part in name:
                    match = False
                    break
            if match:
                j.shows.append(show)
        for movie in movies:
            match = True
            name = movie.name.lower()
            for part in parts:
                if not part in name:
                    match = False
                    break
            if match:
                j.movies.append(movie)
        return t.render(j.kwargs())

class ComingGroup(object):
    def __init__(self):
        self.title = ""
        self.days_away = 0
        self.eps = []

def format_days_away(days, count):
    if days == 0:
        return "Today"
    elif days == 1:
        return "Tomorrow"
    elif days == -1:
        return "Yesterday"
    elif days < -1:
        d2 = "{0} Days Ago".format(days)
    else:
        d2 = "{0} Days".format(days)
    dt = datetime.today()
    dt = dt + timedelta(days=days)
    d1 = '{d:%A}'.format(d=dt)
    return "{0} [{1}]".format(d1, d2)

def format_days_away_2(days, count):
    dt = datetime.today()
    dt = dt + timedelta(days=days)
    if days == 0:
        d2 = "Today"
    elif days == 1:
        d2 = "Tomorrow"
    elif days == -1:
        d2 = "Yesterday"
    elif days < -1:
        d2 = "{0} Days Ago".format(days)
    else:
        d2 = "{0} Days".format(days)
    d1 = '{d:%A} {d.month}/{d.day:02}/{d.year}'.format(d=dt)
    return "{0} ({1} Episodes) [{2}]".format(d1, count, d2)
