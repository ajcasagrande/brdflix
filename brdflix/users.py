import cherrypy
import json
import urllib

import brdflix
from decorators import *
from helpers import *
import xbmc
from db_mysql import DEFAULT as db
from datatypes import *
from webtools import _attempt_login

class UserInterface():
    _cp_config = { 'tools.log_request.on': True,
                   'tools.login_required.on': True }

    @disable_login
    @cherrypy.expose
    def login(self, u=None, p=None, login=None, remember=False, logout=False, referer=None):
        if referer is not None:
            referer = urllib.unquote(referer)
        bad = False
        if u is not None and p is not None:
            # username and password supplied; attempt to login
            user = User().from_name(u)
            # password should be sha-1 hashed before sending as a security measure
            sha_pass = p #hashlib.sha1(p).hexdigest()
            success = user is not None and user.password == sha_pass
            if success:
                cookie_val = "{0}$${1}".format(u, sha_pass)
                cookie_expires = 30 if remember else None
                set_cookie(brdflix.LOGIN_COOKIE, cookie_val, expire_days=cookie_expires)
                #set_cookie(brdflix.LOGIN_COOKIE, cookie_val, expire_days=cookie_expires, domain="stream.<TODO>.com")
                if referer is not None and referer.startswith('/'):
                    raise cherrypy.HTTPRedirect(referer)
                else:
                    raise cherrypy.HTTPRedirect("/index/")
            else:
                bad = True
        if not logout and _attempt_login():
            if referer is not None and referer.startswith('/'):
                raise cherrypy.HTTPRedirect(referer)
            else:
                raise cherrypy.HTTPRedirect("/index/")
        t, j = get_jinja_template("login.html")
        j.bad = bad
        j.referer = urllib.quote(referer) if referer is not None else None
        return t.render(j.kwargs())

    @disable_login
    @cherrypy.expose
    def logout(self):
        clear_cookie(brdflix.LOGIN_COOKIE)
        return self.login(logout=True)

    @cherrypy.expose
    def addFavoriteShow(self, xbmc_id):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        st = time.time()

        # Check if this is already in the user's favorite show list
        existing = FavoriteShow().query_one(xbmc_id=xbmc_id, user_id=cherrypy.request.user.id)
        if existing is not None:
            ms = int((time.time() - st) * 1000)
            return json.dumps({ 'res': { 'ms': ms, 'id': -1, 'status': 'FAIL: User favorite already exists!' } })

        f = FavoriteShow()
        f.user_id = cherrypy.request.user.id
        f.xbmc_id = int(xbmc_id)
        show = xbmc.getShowInfo(f.xbmc_id)
        f.tvdb_id = int(show.tvdb_id)
        f.show_name = show.name
        res = db.insert_generic(f)
        ms = int((time.time() - st) * 1000)
        return json.dumps({ 'res': { 'ms': ms, 'id': res, 'status': 'OK' if int(res) >= 0 else 'FAIL' } })

    @cherrypy.expose
    def removeFavoriteShow(self, xbmc_id):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        st = time.time()
        fave = FavoriteShow().query_one(xbmc_id=xbmc_id, user_id=cherrypy.request.user.id)
        if fave is not None:
            ms = int((time.time() - st) * 1000)
            fave.delete()
            return json.dumps({ 'res': { 'ms': ms, 'id': fave.id, 'status': 'OK' } })
        else:
            ms = int((time.time() - st) * 1000)
            return json.dumps({ 'res': { 'ms': ms, 'id': -1, 'status': 'FAIL: Unable to delete non-existing item' } })

    @cherrypy.expose
    def modifyFaveNotification(self, id, notify):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        st = time.time()
        notify = notify == "True"

        # Check if this is already in the user's favorite show list
        fave = FavoriteShow().query_one(id=int(id), user_id=cherrypy.request.user.id)
        if fave is None:
            ms = int((time.time() - st) * 1000)
            return json.dumps({ 'res': { 'ms': ms, 'id': -1, 'status': 'FAIL: User favorite does not exist!' } })

        fave.notify = 1 if notify else 0
        res = fave.update(['notify'])
        ms = int((time.time() - st) * 1000)
        return json.dumps({ 'res': { 'ms': ms, 'id': res, 'status': 'OK' if int(res) >= 0 else 'FAIL' } })

    @cherrypy.expose
    def addWatchlistItem(self, xbmc_id):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        st = time.time()

        # Check if this is already in the user's watchlist
        existing = WatchlistItem().query_one(xbmc_id=xbmc_id, user_id=cherrypy.request.user.id)
        if existing is not None:
            ms = int((time.time() - st) * 1000)
            return json.dumps({ 'res': { 'ms': ms, 'id': -1, 'status': 'FAIL: User watchlist item already exists!' } })

        w = WatchlistItem()
        w.user_id = cherrypy.request.user.id
        w.xbmc_id = int(xbmc_id)
        movie = xbmc.getMovieInfo(w.xbmc_id)
        w.movie_name = movie.name
        res = db.insert_generic(w)
        ms = int((time.time() - st) * 1000)
        return json.dumps({ 'res': { 'ms': ms, 'id': res, 'status': 'OK' if int(res) >= 0 else 'FAIL' } })

    @cherrypy.expose
    def removeWatchlistItem(self, xbmc_id):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        st = time.time()
        w = WatchlistItem().query_one(xbmc_id=xbmc_id, user_id=cherrypy.request.user.id)
        if w is not None:
            w.delete()
            ms = int((time.time() - st) * 1000)
            return json.dumps({ 'res': { 'ms': ms, 'id': w.id, 'status': 'OK' } })
        else:
            ms = int((time.time() - st) * 1000)
            return json.dumps({ 'res': { 'ms': ms, 'id': -1, 'status': 'FAIL: Unable to delete non-existing item' } })

    @cherrypy.expose
    def config(self):
        t, j = get_jinja_template("user_config.html")
        return t.render(j.kwargs())

    @cherrypy.expose
    def favorites(self):
        t, j = get_jinja_template("user_favorites.html")
        j.faves = FavoriteShow.get_all_from_user(j.user.id)
        return t.render(j.kwargs())
