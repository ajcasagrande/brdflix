import urllib
import cherrypy
import base64
from datetime import datetime

from helpers import *
from decorators import *
from db_mysql import DEFAULT as db
from datatypes import *
import brdflix
import xbmc
from transcode import *
import frametools
import hashes
from img import *
import media_helper

class WatchInterface:
    _cp_config = { 'tools.log_request.on': True,
                   'tools.login_required.on': True }

    @cherrypy.expose
    def file(self, path64, offset=0):
        pass

    @cherrypy.expose
    def trailer(self, movieid, embed="True", offset=0, stretch='False'):
        return self.watchXBMC(movieid=movieid, trailer=True,  embed=(embed == "True"), offset=offset, stretch=stretch)

    @cherrypy.expose
    def movie(self, id, offset=0, stretch='False', resume='False'):
        return self.watchXBMC(movieid=id, offset=offset, stretch=stretch, resume=resume)
        
    @cherrypy.expose
    def episode(self, id, offset=0, stretch='False', resume='False'):
        return self.watchXBMC(episodeid=id, offset=offset, stretch=stretch, resume=resume)

    @cherrypy.expose
    def watchXBMC(self, episodeid=None, movieid=None, trailer=False, embed=False, offset=0, stretch='False', resume='False'):
        user = cherrypy.request.user
        ua = cherrypy.request.headers.get('User-Agent', '')
        isMobile = 'mobile' in ua.lower()

        use_hls = False #'iPad' in ua
        if use_hls:
            t, j = get_jinja_template("watch_video_hls.html")
        else:
            t, j = get_jinja_template("watch_video.html")

        j.autoplay = False
        q_cookie = get_cookie(brdflix.AUTOPLAY_COOKIE)
        if q_cookie is not None:
            j.autoplay = str(q_cookie.value).lower() == "true"

        j.trailer = trailer
        j.embed = embed
        j.episodeid = episodeid
        j.movieid = movieid
        j.showid = None
        j.movie = None
        j.episode = None
        j.prevEp = None
        j.nextEp = None
        j.offset = offset
        
        if movieid is not None:
            j.movie = xbmc.getMovieInfo(movieid)
            j.poster_url = '/img/xbmcImage?path64=' + j.movie.fanart64
            j.path64 = base64.b64encode((j.movie.trailer_file if trailer else j.movie.file).encode("utf-8"))

            if trailer and 'yahoo.com' in j.movie.trailer_file:
                t, j_ignore = get_jinja_template('watch_yahoo.html')
                return t.render(j.kwargs())


#            if trailer and 'yahoo.com' in j.movie.trailer_file:
#                import yahoo
#                yahoo.download_trailer(j.movie)
#            print j.movie.trailer_file
#            print j.path64
            j.watched = j.movie.watched
            
        if episodeid is not None:
            j.episode = xbmc.getEpisodeInfo(episodeid)
            j.showid = int(j.episode.idShow)
            j.poster_url = '/img/xbmcImage?path64=' + j.episode.thumbpath64
            j.path64 = base64.b64encode(j.episode.file.encode("utf-8"))
            j.watched = j.episode.watched
            # determine next and previous episodes
            j.prevEp, j.nextEp = xbmc.getPreviousNextEpisodes(j.episode)

#            server = XBMCServer().query_one(name="<TODO>")
#            if server is not None:
#                pprint(server.__dict__)
#                xbmc.playEpisode(server, episodeid)
#                xbmc.setFullscreen(server, True)
#                return munge("")

        if isMobile:
            j.default_quality_id = user.group.default_mobile_quality_id
            j.max_quality_id = user.group.max_mobile_quality_id
        else:
            j.default_quality_id = user.group.default_quality_id
            j.max_quality_id = user.group.max_quality_id

        j.default_quality = Quality().from_id(j.default_quality_id)
        j.max_quality = Quality().from_id(j.max_quality_id)
        if j.max_quality is not None and j.default_quality.sort_index > j.max_quality.sort_index:
            j.default_quality = j.max_quality

        if j.max_quality is None:
            j.qualities = Quality().query_all()
        else:
            j.qualities = []
            for qual in Quality().query_all():
                if qual.sort_index <= j.max_quality.sort_index:
                    j.qualities.append(qual)

        q_cookie = get_cookie(brdflix.QUALITY_COOKIE)
        if q_cookie is not None:
            cq = Quality().from_id(int(q_cookie.value))
            if cq is not None and (j.max_quality is None or cq.sort_index <= j.max_quality.sort_index):
                j.default_quality = cq
                j.default_quality_id = cq.id
            else:
                clear_cookie(brdflix.QUALITY_COOKIE)

        v_cookie = get_cookie(brdflix.VOLUME_COOKIE)
        if v_cookie is not None:
            j.vol_boost = int(v_cookie.value)
        else:
            j.vol_boost = 256

        media = media_helper.get_or_create_media(j.path64, movieid, episodeid, j.showid, trailer)
        j.media = media
        j.duration = j.media.duration
        j.fname = j.media.fname

        # Determine the human readable size of the file for raw downloading
        raw = j.media.bytes / 1024.0 / 1024.0
        if raw < 1000:
            j.raw_size = "{0} MB".format(int(round(raw)))
        else:
            j.raw_size = "{0} GB".format(round(raw / 1024.0, 2))

        # set thumb frequency to be a percentage of the video
        MAX_THUMBS = 30
        j.thumb_freq = int(round(media.duration / MAX_THUMBS))
        j.enable_thumbs = True

        # HTTP Live Streaming urls
        j.variable_m3u8_base_url = "/hls/variable.m3u8?path64="+j.path64+"&audio_stream="+str(media.audio_stream)
        j.video_m3u8_base_url = "/hls/video.m3u8?path64="+j.path64+"&audio_stream="+str(media.audio_stream)
        j.variable_m3u8_url = j.variable_m3u8_base_url+"&offset="+str(offset)
        j.video_m3u8_url = j.video_m3u8_base_url+"&offset="+str(offset)

        j.show_srt = False

        play = Play(user_id=user.id, request_id=cherrypy.request.request_obj.id, media_id=media.id)
        play.insert()
        j.play = play

        j.login_info = base64.b64encode("{0}$${1}".format(user.username, user.password))

        j.stream_host = get_stream_host()
        #j.stream_host = ''

        j.resume = Resume().query_one(user_id=user.id, media_id=media.id, order_by='`timestamp` desc') if offset == 0 else None
        # Do not resume if the resume point is more than 95% through the video or less than 25 seconds
        if j.resume and (j.resume.offset < 25 or float(j.resume.offset) / media.duration >= 0.95):
            j.resume = None

        remote_xbmc = False
        if remote_xbmc:
            x = j.xbmc_servers[0]
            xs = xbmc.create_local_xbmc_server(x)
            if xs.JSONRPC.Ping():
                print "Ping", x.name, "successful"
                print "Episode Id:", media.episode_id
                xs.Player.Open(item={'episodeid': int(media.episode_id)})
                t2, j2 = get_jinja_template('xbmc_remote.html')
                j2.server = x
                return t2.render(j2.kwargs())

        j.stretch = stretch == 'True'
        j.request_base = cherrypy.request.base
        j.force_resume = resume == 'True'
        return t.render(j.kwargs())

    @disable_log_request
    @cherrypy.expose
    def add_resume(self, user_id, media_id, offset, auto="True"):
        resume = Resume()
        resume.user_id = user_id
        resume.media_id = media_id
        resume.offset = offset
        resume.auto = auto == "True"
        resume.timestamp = datetime.now()
        db.insert_generic(resume)
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps({ 'res': { 'status': 'OK' } })
        
    @cherrypy.expose
    def get_resumes(self, movie_id=None, show_id=None, episode_id=None, path64=None):
        return None

    @cherrypy.expose
    def get_seek_time(self, media_id, s, allow_over="True"):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        frame = frametools.get_closest_media_frame(media_id, float(s), allow_over == "True")
        if frame is not None:
            return json.dumps({ 'res': { 's': '%0.3f' % round(frame.time, 3) , 'f': frame.num, 'valid': True }})
        else:
            return json.dumps({ 'res': { 's': s, 'f': 0, 'valid': False }})
