import cherrypy
import os
import sys
import time
from threading import Thread
from pprint import pprint, pformat
import json

import brdflix
from helpers import *
from decorators import *
from db_mysql import DEFAULT as db
from datatypes import *
from transcode import *
import xbmc
import sickbeard
import hashes
import frametools
import mailer
from missing import *

class AdminInterface:
    _cp_config = { 'tools.log_request.on': True,
                   'tools.login_required.on': True,
                   'tools.login_required.admin_only': True }

    @cherrypy.expose
    def index(self):
        t, j = get_jinja_template('admin.html')
        query = 'select * from play_info order by start_time desc limit 10'
        rows = db.fetch_all(query, None)
        j.recent_plays = [ db.get_generic(DatabaseObject(), row, True) for row in rows ]
        return t.render(j.kwargs())

    @disable_admin_only
    @cherrypy.expose
    def error(self):
        mailer.send_to_admin('BRDFlix Admin Error',
'''
User: {0}

Time: {1}

Request:

{2}
'''.format(cherrypy.request.user.username if cherrypy.request.user is not None else 'N/A',
            datetime.now().strftime('%a, %d-%b-%Y %H:%M:%S'),
            pformat(cherrypy.request.request_obj.__dict__)))
        t, j = get_jinja_template("admin_error.html")
        return t.render(j.kwargs())
        
    @cherrypy.expose
    def config(self):
        t, j = get_jinja_template("site_config.html")
        return t.render(j.kwargs())

    @cherrypy.expose
    def shutdown(self):
        cherrypy.engine.exit()
        return ""

    @cherrypy.expose
    def restart(self):
        thread = Thread(target=do_restart, args=[0.5])
        thread.daemon = True
        thread.start()
        return munge('''
<!DOCTYPE html>
<html>
    <head>
        <title>BRDFlix</title>
        <script type="text/javascript">
            function loadHomepage(){
                window.location = '/';
            }
            setTimeout(loadHomepage, 1500);
        </script>
    </head>
    <body>
        <h1>System Performing Restart</h1>
        <a href="/">Load Home Page</a>
    </body>
</html>
        ''')

    @cherrypy.expose
    def static_restart(self):
        t, j = get_jinja_template("static_restart.html")
        return t.render(j.kwargs())

    @cherrypy.expose
    def restart_json(self):
        thread = Thread(target=do_restart, args=[0.5])
        thread.daemon = True
        thread.start()
        return json.dumps({ 'res': 'OK' })

    @cherrypy.expose
    def missing(self):
        st = time.time()
        t, j = get_jinja_template("missing.html")
        shows = xbmc.getShows()
        j.missing = []
        for show in shows:
            mshow = getMissing(show)
            if mshow.total > 0:
                j.missing.append(mshow)
        j.missing = sorted(j.missing, key=lambda m: m.total)
        j.sb_base_url = sickbeard.getHtmlBaseUrl()
        j.acc = "#accordion_main"
        for mshow in j.missing:
            if len(mshow.seasons) > 1:
                j.acc = j.acc  + ",#accordian_" + str(mshow.tvdb_id)
        ms = int((time.time() - st) * 1000)
        print "Missing Episodes - Finsihed in", ms, "ms"
        return t.render(j.kwargs())

    @cherrypy.expose
    def index_all_tv(self):
        shows = xbmc.getShows(sort_method="random")
        for show in shows:
            self.index_episodes(show.id)

    @cherrypy.expose
    def index_episodes(self, show_id):
        begin = time.time()
        seasons = xbmc.getSeasons(show_id)
        for season in seasons:
            eps = xbmc.getEpisodes(show_id, season.num)
            for ep in eps:
                path64 = base64.b64encode(ep.file.encode("utf-8"))
                nm = xbmc.getLocalPathFromPath64(path64)
                hash = hashes.quick(nm)
                media = Media().from_sha1(hash.value)
                start = time.time()
                if media is None:
                    print "Indexing:", ep.fname
                    # Use ffprobe to ensure correct duration
                    info = getVideoInfo(nm)

                    media = Media()
                    media.update_hash(hash)
                    media.update_video_info(info)
                    media.path64 = path64
                    media.fname = nm[nm.rfind(u'/')+1:]
                    media.is_trailer = False
                    media.show_id = show_id
                    media.episode_id = ep.id
                    media.movie_id = None
                    db.insert_generic(media)

                row = db.fetch_one('select count(*) as total from media_frame where media_id=%s', (media.id,))
                if int(row['total']) == 0:
                    print "Generating media frames:", ep.fname
                    frametools.generate_media_index(media, True)
                    print "Finished indexing in", time.time() - start, "seconds"
        print "Finished indexing all episodes in", time.time() - begin, "seconds"

def do_restart(wait_time=0.5):
    time.sleep(wait_time)
    args = [sys.executable] + sys.argv
    if sys.platform == "win32":
        args = ['"%s"' % arg for arg in args]
    new_environ = os.environ.copy()
    new_environ["RUN_MAIN"] = 'true'
    print "\nSHUTTING DOWN CHERRYPY SERVER!\n"
    exit_code = os.execve(sys.executable, args, new_environ)
