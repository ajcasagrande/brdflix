import cherrypy
from cherrypy.lib.static import serve_file

from helpers import *
from decorators import *
from db_mysql import DEFAULT as db
from datatypes import *
from transcode import *
import brdflix
import frametools
import settings

class HLSInterface:
    _cp_config = { 'tools.log_request.on': True,
                   'tools.login_required.on': True }


    @cherrypy.expose
    def ffms_m3u8(self, play_id, path64, bitrate=1000, width=854, volume=512, video_stream=0, audio_stream=1, segment_length=10):
        m3u8 = '''#EXTM3U
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-TARGETDURATION:{0}
'''.format(segment_length)

        path = os.path.join(settings.GLOBAL.temp_dir, 'ffindex')
        fname = os.path.join(path, str(play_id) + '.ffindex_track00.kf.txt')
        if os.path.isfile(fname):
            segments = frametools.get_segments(frametools.create_key_timecodes(fname, '24000/1001'), segment_length)
        else:
            segments = frametools.get_segments(frametools.create_key_timecodes(frametools.generate_index(play_id, path64, True), '24000/1001'), segment_length)
        for offset, duration in segments:
            stream = '''#EXTINF:{0},
/hls/segment.ts?play_id={8}&offset={1}&duration={0}&bitrate={2}&width={3}&video_stream={4}&audio_stream={5}&volume={6}&path64={7}
'''.format(duration, offset, bitrate, width, video_stream, audio_stream, volume, path64, play_id)
            m3u8 += stream

        m3u8 += '#EXT-X-ENDLIST\n'
        cherrypy.response.headers['Content-Type'] = 'application/vnd.apple.mpegurl'
        return munge(m3u8)

    @cherrypy.expose
    def variable_m3u8(self, path64, offset=0, volume=512, audio_stream=1):
        m3u8 = '''#EXTM3U
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=1280000
/hls/video.m3u8?path64={0}&offset={1}&volume={2}&audio_stream={3}&bitrate=500&width=360
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=480000
/hls/video.m3u8?path64={0}&offset={1}&volume={2}&audio_stream={3}&bitrate=300&width=360
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=2560000
/hls/video.m3u8?path64={0}&offset={1}&volume={2}&audio_stream={3}&bitrate=1000&width=854
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=7680000
/hls/video.m3u8?path64={0}&offset={1}&volume={2}&audio_stream={3}&bitrate=2000&width=1280
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=17680000
/hls/video.m3u8?path64={0}&offset={1}&volume={2}&audio_stream={3}&bitrate=3500&width=1280
'''.format(path64, offset, volume, audio_stream)
        cherrypy.response.headers['Content-Type'] = 'application/vnd.apple.mpegurl'
        return munge(m3u8)
    
    @cherrypy.expose
    def video_m3u8(self, path64, offset=0, volume=512, bitrate=500, width=854, audio_stream=1):
        fname = xbmc.getLocalPathFromPath64(path64)
        details = "{0}_{1}_{2}_{3}".format(offset, bitrate, width, audio_stream)
        sha1 = hashlib.sha1(fname).hexdigest()
        cwd = os.path.join(settings.GLOBAL.temp_dir, sha1, details)
        if not os.path.exists(cwd):
            os.makedirs(cwd)
        playlist = cwd + "/out.m3u8"

        if os.path.isfile(playlist):
            cherrypy.response.headers['Content-Type'] = 'application/vnd.apple.mpegurl'
            f = open(playlist, 'r')
            s = f.read()
            s = s.replace('out_', '/hls/ts?sha1='+sha1+'&details='+details+'&file=out_')
            f.close()
            return munge(s)
        else:
            p = TranscodeProcess()
            p.offset = offset
            p.volume = volume
            p.bitrate = bitrate
            p.width = width
            p.audio_stream = audio_stream
            p.fname = fname
            # p.show_srt = True
            # p.srt_fname = p.fname[:p.fname.rfind('.')] + ".en.ass";
            # print p.srt_fname
            p.setup('m3u8')
            p.run_m3u8(cherrypy.request.user, cwd, sha1, details)
            
            cherrypy.response.headers['Content-Type'] = 'application/vnd.apple.mpegurl'
            while not os.path.isfile(playlist):
                time.sleep(0.2)
            while True:
                with open(playlist, 'r') as pl:
                    s = pl.read()
                    if 'out_' in s:
                        s = s.replace('out_', '/hls/ts?sha1='+sha1+'&details='+details+'&file=out_')
                        break  
            return munge(s)
    
    @cherrypy.expose
    def ts(self, sha1, details, file):
        return serve_file(os.path.join(settings.GLOBAL.temp_dir, sha1, details, file), "video/MP2T")
    
    @cherrypy.expose
    def segment_ts(self, play_id, offset, duration, path64, volume=1024, bitrate=1000, width=854, video_stream=0, audio_stream=1):
        p = TranscodeProcess()
        p.offset = offset
        #p.offset = int(float(offset))
        #p.offset2 = float(offset) - p.offset
        p.duration = duration
        p.volume = volume
        p.bitrate = bitrate
        p.width = width
        p.video_stream = video_stream
        p.audio_stream = audio_stream
        p.fname = xbmc.getLocalPathFromPath64(path64)
        p.setup('segment_ts')
        #print p.cmd
        print p.bitrate, 'kb/s'

        stream = Stream()
        stream.update_process(p)
        stream.user_id = cherrypy.request.user.id
        stream.path64 = path64
        stream.format = 'segment_ts' # should this be 'segment_ts' or just 'ts'?
        stream.quality_id = 0 # TODO
        stream.play_id = int(play_id)
        stream.request_id = cherrypy.request.request_obj.id
        db.insert_generic(stream)
        cherrypy.request.stream_obj = stream
        p.stream_obj = stream

        p.run_monitored(interval=1.0, timeout=3.0)

        cherrypy.request.transcode_process = p
        cherrypy.response.headers['Content-Type'] = 'video/MP2T'

#        cherrypy.response.stream = True
#        return p.result(boost_seconds=3, max_mbps=3.0)
        cherrypy.response.stream = False
        return p.process.communicate()[0]

    @cherrypy.expose
    def dynamic_m3u8(self, path64, bitrate=1000, width=854, volume=512, video_stream=0, audio_stream=1):
        m3u8_file = getM3U8File(xbmc.getLocalPathFromPath64(path64))
        with open(m3u8_file, 'r') as f:
            data = f.read()
            data = data.replace('/hls/segment.ts?', '/hls/segment.ts?bitrate={0}&width={1}&video_stream={2}&audio_stream={3}&volume={4}&'.format(bitrate, width, video_stream, audio_stream, volume)) 
            cherrypy.response.headers['Content-Type'] = 'application/vnd.apple.mpegurl'
            return data

    @cherrypy.expose
    def variable_dynamic_m3u8(self, path64, volume=512, video_stream=0, audio_stream=1):
        m3u8_file = getM3U8File(xbmc.getLocalPathFromPath64(path64))
        m3u8 = '''#EXTM3U
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=1280000
/hls/dynamic.m3u8?path64={0}&volume={1}&audio_stream={2}&video_stream={3}&bitrate=500&width=360
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=640000
/hls/dynamic.m3u8?path64={0}&volume={1}&audio_stream={2}&video_stream={3}&bitrate=300&width=360
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=2560000
/hls/dynamic.m3u8?path64={0}&volume={1}&audio_stream={2}&video_stream={3}&bitrate=1000&width=854
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=5120000
/hls/dynamic.m3u8?path64={0}&volume={1}&audio_stream={2}&video_stream={3}&bitrate=2000&width=1280
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=12800000
/hls/dynamic.m3u8?path64={0}&volume={1}&audio_stream={2}&video_stream={3}&bitrate=3500&width=1280
'''.format(path64, volume, audio_stream, video_stream)
        cherrypy.response.headers['Content-Type'] = 'application/vnd.apple.mpegurl'
        return munge(m3u8)
