import cherrypy
from threading import Thread
import time
import base64
from PIL import Image
from cStringIO import StringIO

import xbmc
from decorators import *
from helpers import *
import frametools
from datatypes import *
import img as img_
from transcode import *
import settings

class TestingGrounds:
    _cp_config = { 'tools.log_request.on': True,
                   'tools.login_required.on': True }

    @cherrypy.expose
    def index(self):
        return "Testing Grounds"
     
    @cherrypy.expose
    def error(self):
        open('A:/this/file/does/not/exist')
        return None

    @cherrypy.expose
    def t1(self):
        st = time.time()
        shows = xbmc.getShows()
        for show in shows:
            xbmc.getShowStats(show.id)
        sec = time.time() - st
        return munge("Finished in {0} seconds".format(sec))
        
    @cherrypy.expose
    def t2(self):
        st = time.time()
        threads = []
        shows = xbmc.getShows()
        for show in shows:
            thread = Thread(target=xbmc.getShowStats, args=[show.id])
            thread.daemon = True
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
        sec = time.time() - st
        return munge("Finished in {0} seconds".format(sec))    

    @cherrypy.expose
    def t3(self):
        path64 = base64.b64encode(r"S:\TV Shows\Archer (2009)\Season 00\Archer (2009) - 0x04 - Heart of Archness Part I.mkv")
        segments = frametools.get_segments(frametools.create_key_timecodes(frametools.generate_index(400, path64, True), '24000/1001'), 10)
        return '<br/>'.join([ "offset={0:.3f}&duration={1:.3f}".format(offset, round(dur, 3)) for offset, dur in segments ])

    @cherrypy.expose
    def t4(self):
        from hls import HLSInterface
        path64 = base64.b64encode(r"S:\TV Shows\Archer (2009)\Season 00\Archer (2009) - 0x04 - Heart of Archness Part I.mkv")
        return HLSInterface().ffms_m3u8(path64)

    @cherrypy.expose
    def t5(self):
        quals = Quality().query_all()
        for q in quals:
            q.dump()

    @cherrypy.expose
    def t6(self):
        media = Media().query_all()[0]
        start = time.time()
        MAX_THUMBS = 60
        thumb_freq = int(round(media.duration / MAX_THUMBS))
        count = 0
        i = 0
        while i < media.duration:
            offset = i if i > 5 else 5
            print "Generating @", offset, "seconds..."
            res = img_.generate_thumb(media.path64, offset=offset, width=108, height=60, outname='C:/out/'+str(i)+'.jpg')
            count += 1
            i += thumb_freq
        print "Generated", count, "images in", time.time() - start, "seconds"

    @cherrypy.expose
    def t7(self):
        media = Media().query_all()[0]
        start = time.time()
        MAX_THUMBS = 300
        frequency = int(round(media.duration / MAX_THUMBS))

        linelength = 8
        spritelength = MAX_THUMBS

        NUM_X = int(linelength)
        TOTAL = int(spritelength)
        NUM_Y = TOTAL / NUM_X
        WIDTH = 108
        HEIGHT = 60

        images = []
        count = 0
        i = 0
        while i <= media.duration:
            offset = i if i > 5 else 5
            print "Generating @", offset, "seconds..."
            fname = 'C:/out/'+str(i)+'.jpg'
            res = img_.generate_thumb(media.path64, offset=offset, width=108, height=60)
            images.append(res)
            count += 1
            i += frequency
        print "Generated", count, "images in", time.time() - start, "seconds"

        print NUM_X, NUM_Y, TOTAL
        sprite = Image.new('RGB', (WIDTH * NUM_X, HEIGHT * NUM_Y), (0,0,0))
        print WIDTH * NUM_X, 'x', HEIGHT * NUM_Y
        i = 0
        for y in range(NUM_Y):
            for x in range(NUM_X):
                try:
                    io = StringIO(images[i])
                    img = Image.open(io)
                except (IOError, IndexError) as ex:
                    img = Image.new('RGB', (WIDTH, HEIGHT), (0,0,0))
                    print "Error opening image"
                sprite.paste(img, (x * WIDTH, y * HEIGHT, (x + 1) * WIDTH, (y + 1) * HEIGHT))
                if io:
                    io.close()
                if img:
                    del img
                i += 1
        buffer = StringIO()
        sprite.save(buffer, 'JPEG', quality=85, optimize=True)
        #sprite.save('C:/out/out.jpg', 'JPEG', quality=85, optimize=True)
        cherrypy.response.headers['Content-Type'] = 'image/jpeg'
        val = buffer.getvalue()
        buffer.close()
        del sprite
        return val

    @cherrypy.expose
    def t8(self):
        media = Media().query_all()[1]
        fname = xbmc.getLocalPathFromPath64(media.path64)
        start = time.time()
        duration = 60
        offset = 0
        count = 0
        while offset < media.duration:
            print "Generating @", offset, "seconds..."

            p = TranscodeProcess()
            p.offset = offset
            p.duration = duration
            p.fname = fname

            path = os.path.join(settings.GLOBAL.temp_dir, media.sha1, 'thumbs', str(offset))
            if not os.path.exists(path):
                os.makedirs(path)

            p.outfile = os.path.join(path, '%02d.jpg')

            p.setup('key_thumbs')
            p.run()
#            thread = Thread(target=p.process.communicate)
#            thread.daemon = True
#            thread.start()
            p.process.communicate()
            # delete the process to clean up handles
            del p.process

            offset += duration
            count += 1
        print "Generated", count, "images in", time.time() - start, "seconds"

    @cherrypy.expose
    def t9(self):
        media = Media().query_all()[1]
        fname = xbmc.getLocalPathFromPath64(media.path64)
        start = time.time()

        print "Generating all key thumbs..."

        p = TranscodeProcess()
        p.fname = fname

        path = os.path.join(settings.GLOBAL.temp_dir, media.sha1, 'thumbs', 'all')
        if not os.path.exists(path):
            os.makedirs(path)

        p.outfile = os.path.join(path, '%04d.jpg')

        p.setup('key_thumbs_all')
        p.run()
        p.process.communicate()
        # delete the process to clean up handles
        del p.process

        print "Generated", "all", "thumbs in", time.time() - start, "seconds"
