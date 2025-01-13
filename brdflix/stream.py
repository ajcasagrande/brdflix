import cherrypy
from cherrypy.lib.static import serve_file
import sys
import json

from helpers import *
from decorators import *
from db_mysql import DEFAULT as db
from datatypes import *
from transcode import *
import brdflix
from img import *
import frametools
import settings
import webtools
import xbmc
import media_helper

class StreamInterface:
    # Do not require login because stream works based on different method

    _cp_config = { 'tools.log_request.on': True,
                   'tools.login_required.on': False }

    @cherrypy.expose
    def srt_srt(self, path64, offset=0):
        fname = base64.b64decode(path64)
        return serve_file(fname, 'text/plain')

    @cherrypy.expose
    def srt(self, media_id, stream_index=2, offset=0):
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = "*"
        outpath = os.path.join(settings.GLOBAL.temp_dir, 'srt')
        if not os.path.exists(outpath):
            os.makedirs(outpath)
        outfile = os.path.join(outpath, '{0}_{1}_{2}.srt'.format(media_id, stream_index, offset))
        if os.path.isfile(outfile):
            # File already exists, lets just serve that
            return serve_file(outfile)
        media = Media().from_id(media_id)

        p = TranscodeProcess()
        p.offset = offset
        p.srt_stream = int(stream_index)
        p.fname = xbmc.getLocalPathFromPath64(media.path64)
        p.outfile = outfile
        p.setup('srt')

        p.run(print_cmd=True)
        p.process.communicate()
        return serve_file(outfile)

    @cherrypy.expose
    def transcode_flv(self, play_id, media_id, offset=0, volume=1024, quality=0, crop_3d='False', zl=""):
        print cherrypy.request.query_string
        print offset
        return self.transcode(play_id, media_id, format='flv', offset=offset, volume=volume, quality=quality, crop_3d=crop_3d, zl=zl)

    @cherrypy.expose
    def transcode_webm(self, play_id, media_id, offset=0, volume=1024, quality=0, crop_3d='False', zl=""):
        return self.transcode(play_id, media_id, format='webm', offset=offset, volume=volume, quality=quality, crop_3d=crop_3d, zl=zl)

    @cherrypy.expose
    def transcode_ogv(self, play_id, media_id, offset=0, volume=1024, quality=0, crop_3d='False', zl=""):
        return self.transcode(play_id, media_id, format='ogv', offset=offset, volume=volume, quality=quality, crop_3d=crop_3d, zl=zl)

    @cherrypy.expose
    def public_transcode_flv(self, guid):
        link = PublicLink().from_id(guid)
        if link is not None:
            media = Media().from_id(link.media_id)
            q = Quality().from_id(link.quality_id)

            p = TranscodeProcess()
            p.offset = link.start_time
            p.duration = link.end_time - link.start_time
            p.volume = 128
            p.bitrate = q.bitrate
            p.width = q.width
            p.video_stream = media.video_stream
            p.audio_stream = media.audio_stream
            p.fname = xbmc.getLocalPathFromPath64(media.path64)
            p.media_id = media.id
            p.setup('flv_segment')

            p.run()

            cherrypy.request.transcode_process = p
            cherrypy.response.headers['Content-Type'] = 'video/x-flv'
            cherrypy.response.stream = True
            return p.result_old()

    @cherrypy.expose
    def episode(self, id, format='flv', offset=0, volume=1024, quality=0, crop_3d='False', zl=""):
        webtools.login_from_zl(zl, True)
        # Create a media from xbmc episode id
        episode = xbmc.getEpisodeInfo(id)
        path64 = base64.b64encode(episode.file.encode("utf-8"))
        media = media_helper.get_or_create_media(path64, None, int(id), episode.idShow, False)
        # Create a play
        play = Play(user_id=cherrypy.request.user.id, request_id=cherrypy.request.request_obj.id, media_id=media.id)
        play.insert()
        # Send transcode
        return self.transcode(play.id, media.id, format, offset, volume, quality, crop_3d, zl)

    @cherrypy.expose
    def transcode(self, play_id, media_id, format='flv', offset=0, volume=1024, quality=0, crop_3d='False', zl=""):
        webtools.login_from_zl(zl, True)

        media = Media().from_id(media_id)
        if media is None:
            return None

        user = cherrypy.request.user
        q = Quality().from_id(quality)
        max_q = Quality().from_id(user.group.max_quality_id)

        if q is None:
            # QUALITY DOES NOT EXIST
            clear_cookie(brdflix.QUALITY_COOKIE, path=None)
            return brdflix.ADMIN_INTERFACE.error()

        if max_q is not None and q.sort_index > max_q.sort_index:
            # QUALITY IS NOT PERMITTED!
            clear_cookie(brdflix.QUALITY_COOKIE, path=None)
            return brdflix.ADMIN_INTERFACE.error()

        p = TranscodeProcess()
        p.offset = offset
        p.volume = volume
        p.bitrate = q.bitrate
        p.width = q.width
        p.video_stream = media.video_stream
        p.audio_stream = media.audio_stream
        p.fname = xbmc.getLocalPathFromPath64(media.path64)
        # p.show_srt = True
        # p.srt_fname = p.fname[:p.fname.rfind('.')] + ".en.ass";
        # print p.srt_fname
        p.media_id = media.id

        p.media = media
        # Round to nearest even for video size, because libx264 does not work with odd number sizes
        p.height = round_to_even(float(media.height) / media.width * q.width)
        p.crop_3d_sbs = crop_3d == 'True'

        p.setup_jinja(format)

        stream = Stream()
        stream.update_process(p)
        stream.user_id = cherrypy.request.user.id
        stream.format = format
        stream.quality_id = int(quality)
        stream.play_id = int(play_id)
        stream.request_id = cherrypy.request.request_obj.id
        stream.media_id = media_id
        db.insert_generic(stream)
        cherrypy.request.stream_obj = stream
        p.stream_obj = stream

        p.run(True)

        cherrypy.request.transcode_process = p

        print "format: {0}, offset: {1}, volume: {2}, bitrate: {3}, width: {4}".format(format, offset, volume, q.bitrate, q.width)

        if format == 'flv':
            cherrypy.response.headers['Content-Type'] = 'video/x-flv'
        elif format == 'webm':
            cherrypy.response.headers['Content-Type'] = 'video/webm'
        elif format == 'ogv':
            cherrypy.response.headers['Content-Type'] = 'video/ogg'
        cherrypy.response.stream = True
        max_mbps = p.bitrate / 1024.0 * user.group.mbps_multiplier
        if user.group.max_mbps is not None and max_mbps > user.group.max_mbps:
            print "Warning: bitrate * mbps_multiplier = {0}, is higher than max_mbps of {1}. Capping at {1}.".format(max_mbps, user.group.max_mbps)
            max_mbps = user.group.max_mbps
        return p.result(max_mbps=max_mbps, boost_seconds=user.group.boost_seconds, boost_mbps=user.group.boost_mbps)

    @disable_log_request
    @cherrypy.expose
    def preview_multi(self, media_id, name, frequency=1, linelength=1, spritelength=1):
        start = time.time()
        p = TranscodeProcess()
        media = Media().from_id(media_id)
        p.fname = xbmc.getLocalPathFromPath64(media.path64)

        NUM_X = int(linelength)
        TOTAL = int(spritelength)
        NUM_Y = TOTAL / NUM_X
        WIDTH = 108
        HEIGHT = 60

        num = int(name.replace('.jpg', ''))
        offset = num * (int(frequency) * TOTAL)
        p.offset = offset
        p.frequency = frequency
        p.duration = TOTAL * int(frequency)
        p.width = WIDTH
        p.height = HEIGHT
        sha1 = hashlib.sha1(p.fname).hexdigest()
        TEMP_PATH = os.path.join(settings.GLOBAL.temp_dir, sha1, "thumbs", "{0}_{1}".format(offset, frequency))
        if not os.path.exists(TEMP_PATH):
            os.makedirs(TEMP_PATH)
        p.cwd = TEMP_PATH

        print NUM_X, NUM_Y, TOTAL, offset
        p.setup('thumb_multi')

        p.run()

        cherrypy.response.headers['Content-Type'] = 'image/jpeg'
        res = p.process.communicate()[0]
        # delete the process to clean up handles
        del p.process

        sprite = Image.new('RGB', (WIDTH * NUM_X, HEIGHT * NUM_Y), (0,0,0))
        i = 1
        for y in range(NUM_Y):
            for x in range(NUM_X):
                try:
                    img = Image.open(os.path.join(TEMP_PATH, "thumb_%03d.jpg" % (i)))
                    #img = img.resize((WIDTH, HEIGHT), Image.ANTIALIAS)
                except IOError:
                    img = Image.new('RGB', (WIDTH, HEIGHT), (0,0,0))
                sprite.paste(img, (x * WIDTH, y * HEIGHT, (x + 1) * WIDTH, (y + 1) * HEIGHT))
                i = i + 1
        buffer = StringIO()
        sprite.save(buffer, 'JPEG', quality=85, optimize=True)
        end = time.time()
        print "Finished in:", end - start
        return buffer.getvalue()

    @disable_log_request
    @cherrypy.expose
    def preview(self, media_id, name, frequency=25):
        media = Media().from_id(media_id)
        if media is None:
            return None
        WIDTH = 216 #108
        HEIGHT = 120 #60
        num = int(name.replace('.jpg', ''))
        offset = num * int(frequency)
        if num == 0 and int(frequency) > 5:
            offset = 5
        cherrypy.response.headers['Content-Type'] = 'image/jpeg'
        return generate_thumb(media.path64, offset=offset, width=WIDTH, height=HEIGHT, outname=None)

    @login_required
    @cherrypy.expose
    def raw_download(self, media_id):
        if not cherrypy.request.user.group.download_rights:
            return "Download Denied!"
        media = Media().from_id(media_id)
        if media is None:
            raise cherrypy.HTTPError(500, 'Unknown media id.')
        fname = xbmc.getLocalPathFromPath64(media.path64)

        # Headers to make data download not attempt to play
        cherrypy.response.headers['Content-Type'] = 'application/octet-stream'
        cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="' + media.fname + '"'

        # TODO: Find some sort of way to limit the transfer rate
        # Serve the file via streaming
        cherrypy.response.stream = True
        return serve_file(fname)

    @login_required
    @cherrypy.expose
    def transcode_download(self, media_id, format='flv', volume=256, quality=0):
        if not cherrypy.request.user.group.download_rights:
            return "Download Denied!"
        media = Media().from_id(media_id)
        if media is None:
            raise cherrypy.HTTPError(500, 'Unknown media id.')

        # Replace the file extension with the format name
        fname = media.fname[:media.fname.rfind('.')+1] + format
        # Headers to make data download not attempt to play
        cherrypy.response.headers['Content-Type'] = 'application/octet-stream'
        cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="' + fname + '"'

        user = cherrypy.request.user
        q = Quality().from_id(quality)
        max_q = Quality().from_id(user.group.max_quality_id)

        if q is None:
            # QUALITY DOES NOT EXIST
            clear_cookie(brdflix.QUALITY_COOKIE, path=None)
            return brdflix.ADMIN_INTERFACE.error()

        if max_q is not None and q.sort_index > max_q.sort_index:
            # QUALITY IS NOT PERMITTED!
            clear_cookie(brdflix.QUALITY_COOKIE, path=None)
            return brdflix.ADMIN_INTERFACE.error()

        p = TranscodeProcess()
        p.offset = 0
        p.volume = volume
        p.bitrate = q.bitrate
        p.width = q.width
        p.video_stream = media.video_stream
        p.audio_stream = media.audio_stream
        p.fname = xbmc.getLocalPathFromPath64(media.path64)
        p.media_id = media.id
        p.setup(format)

        stream = Stream()
        stream.update_process(p)
        stream.user_id = cherrypy.request.user.id
        stream.format = format
        stream.quality_id = int(quality)
        stream.play_id = -1
        stream.request_id = cherrypy.request.request_obj.id
        stream.media_id = media_id
        cherrypy.request.stream_obj = stream
        p.stream_obj = stream

        print "Transcode download:", media.fname, q.bitrate / 1000, "Mbps"
        p.run()

        cherrypy.request.transcode_process = p

        cherrypy.response.stream = True
        max_mbps = p.bitrate / 1024.0 * user.group.download_multiplier
        if user.group.max_mbps is not None and max_mbps > user.group.max_mbps:
            print "Warning: bitrate * mbps_multiplier = {0}, is higher than max_mbps of {1}. Capping at {1}.".format(max_mbps, user.group.max_mbps)
            max_mbps = user.group.max_mbps
        return p.result(max_mbps=max_mbps, boost_seconds=user.group.boost_seconds, boost_mbps=user.group.boost_mbps)

    @cherrypy.expose
    def thumbs_vtt(self, media_id, freq=10):
        t, j = get_jinja_template('other/thumbs_vtt.html')
        j.freq = int(freq)
        media = Media().from_id(media_id)
        if media is None:
            return None
        j.media = media
        j.segments = []
        index = 0
        i = 0
        while i < media.duration:
            seg = ThumbSegement()
            seg.start_time = i
            seg.end_time = i + j.freq
            if seg.end_time > media.duration:
                seg.end_time = media.duration
            seg.index = index
            i += j.freq
            index += 1
            j.segments.append(seg)
        j.stream_host = get_stream_host()
        cherrypy.response.headers['Access-Control-Allow-Origin'] = "*"
        # Pre-generate all thumbs
        media_helper.generate_thumbs(media, j.segments, 216, 120)
        return t.render(j.kwargs())

    @disable_log_request
    @cherrypy.expose
    def thumb_jpg(self, media_id, offset):
        media = Media().from_id(media_id)
        if media is None:
            return None
        WIDTH = 216 #108
        HEIGHT = 120 #60
        if float(offset) == 0:
            offset = 5
        cherrypy.response.headers['Content-Type'] = 'image/jpeg'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = "*"
        cache_name = os.path.join(settings.GLOBAL.temp_dir, 'thumbs', str(media.id), '{0}.jpg'.format(offset))
        if os.path.isfile(cache_name):
            return serve_file(cache_name)
        return generate_thumb(media.path64, offset=float(offset), width=WIDTH, height=HEIGHT, outname=cache_name)

