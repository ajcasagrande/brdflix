import cherrypy
import json

from helpers import *
from decorators import *
from db_mysql import DEFAULT as db
from datatypes import *
import brdflix
import xbmc
import mailer

class XBMCInterface:
    _cp_config = { 'tools.log_request.on': True,
                   'tools.login_required.on': True }

    @admin_only
    @cherrypy.expose
    def setMovieWatched(self, movieid, watched="True"):
        st = time.time()
        res = xbmc.setMovieWatched(int(movieid), watched == "True")
        ms = int((time.time() - st) * 1000)
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps({ 'res': { 'ms': ms, 'status': res } })

    @admin_only
    @cherrypy.expose
    def setEpisodeWatched(self, episodeid, watched="True"):
        st = time.time()
        res = xbmc.setEpisodeWatched(int(episodeid), watched == "True")
        ms = int((time.time() - st) * 1000)
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps({ 'res': { 'ms': ms, 'status': res } })

    @admin_only
    @cherrypy.expose
    def performScan(self, folder=None):
        st = time.time()
        res = xbmc.performScan(folder)
        ms = int((time.time() - st) * 1000)
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps({ 'res': { 'ms': ms, 'status': res } })

    @cherrypy.expose
    def error(self):
        t, j = get_jinja_template("xbmc_error.html")
        return t.render(j.kwargs())

    @cherrypy.expose
    def check_new(self):
        # Get all recent episodes
        recent = xbmc.getRecentEpisodes()
        # Get all users who have email notifications enabled
        users = User().query_all(allow_email=True)
        for user in users:
            notify = []
            # Get the user's favorite shows and previous email alerts
            faves = FavoriteShow.get_all_from_user(user.id)
            fave_ids = [ fave.xbmc_id for fave in faves ]
            emails = EmailNotification.get_all_from_user(user.id)
            email_eps = [ email.episode_id for email in emails ]
            for ep in recent:
                if ep.idShow in fave_ids and not ep.id in email_eps:
                    # Add to list of episodes to notify about if it is a favorite
                    # and we haven't notified them about it before
                    notify.append(ep)
            if len(notify) > 0:
                # Notify the user via email
                t, j = get_jinja_template("email/new_episodes_email.html")
                j.eps = notify
                j.username = user.username
                j.base_url = settings.GLOBAL.base_url.rstrip('/')
                body = t.render(j.kwargs())
                shows = ", ".join(set([ ep.showName for ep in j.eps ]))
                subject = "New Episodes: " + shows
                mailer.send(user.email, subject, body, is_html=True)

                # Save into database that we sent an email about this new episode
                for ep in notify:
                    e = EmailNotification()
                    e.user_id = user.id
                    e.episode_id = ep.id
                    e.insert()

    @cherrypy.expose
    def play_pause(self, server_id):
        server = XBMCServer().from_id(int(server_id))
        xs = xbmc.create_local_xbmc_server(server)
        res = xs.Player.PlayPause(playerid=1)
        return json.dumps({ 'res': { 'status': 'OK' if res == "speed" else 'FAIL' } })

    @cherrypy.expose
    def stop(self, server_id):
        server = XBMCServer().from_id(int(server_id))
        xs = xbmc.create_local_xbmc_server(server)
        res = xs.Player.Stop(playerid=1)
        return json.dumps({ 'res': { 'status': 'OK' if res == "OK" else 'FAIL' } })


