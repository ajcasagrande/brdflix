import cherrypy
import os
import shutil
import sys
import threading

import brdflix
from brdflix.webserve import WebInterface
from brdflix.testing import TestingGrounds
from brdflix.users import UserInterface
from brdflix.admin import AdminInterface
from brdflix.stream import StreamInterface
from brdflix.watch import WatchInterface 
from brdflix.movies import MovieInterface
from brdflix.tv import TVInterface
from brdflix.img import ImageInterface
from brdflix.xbmc_interface import XBMCInterface
from brdflix.hls import HLSInterface
from brdflix.sickbeard import SickBeardInterface
from brdflix.charts import ChartsInterface
from brdflix.download import DownloadInterface
from brdflix.public_interface import PublicInterface
from brdflix import error_pages

def init_web_server():
        assert isinstance(brdflix.PORT, int)

        # CherryPy setup
        cherrypy.config.update({
            'server.socket_port': brdflix.PORT,
            'server.socket_host': '0.0.0.0',
            'tools.gzip.on': True,
            'tools.process_request.on': True,
            'server.thread_pool': 30,

            'error_page.500': error_pages._500,
            'error_page.403': error_pages._403,
            'error_page.503': error_pages._503,

            'log.screen': False,
            #'log.access_file': brdflix.CHERRYPY_LOG,
            
            ## HTTPS Setup
             #'server.ssl_module': 'builtin',
             #'server.ssl_certificate': os.path.join(brdflix.CERTS_DIR, 'ssl-unified.crt'),
             #'server.ssl_private_key': os.path.join(brdflix.CERTS_DIR, 'ssl_decrypted.key'),
        })

        conf = {
            '/': {
                'tools.staticdir.root': brdflix.DATA_DIR,
                'tools.encode.on': True,
                'tools.encode.encoding': 'utf-8'
            },
            '/images': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': 'images',
                'tools.staticdir.content_types': {'png': 'image/png'}
            },
            '/js':     {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': 'js'
            },
            '/css':    {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': 'css'
            },
            '/flash':    {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': 'flash'
            },
            '/jwplayer':    {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': 'jwplayer',
                'tools.staticdir.content_types': {'png': 'image/png'}
            },
            '/jwplayer6':    {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': 'jwplayer6',
                'tools.staticdir.content_types': {'png': 'image/png'}
            },
            '/jwplayer_6_8':    {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': 'jwplayer_6_8',
                'tools.staticdir.content_types': {'png': 'image/png'}
            },
            '/jqwidgets':    {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': 'jqwidgets'
            },
            '/temp': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': 'temp',
                'tools.staticdir.content_types': {'ts': 'video/MP2T',
                                        'm3u8': 'application/vnd.apple.mpegurl'}
            },
            '/highcharts':    {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': 'highcharts'
            },
            "/favicon.ico": {
                "tools.staticfile.on": True,
                "tools.staticfile.filename": os.path.join(brdflix.IMAGES_DIR, 'movie.ico')
            }
        }
        
        stream_conf = {
            '/': {
                'tools.transcode_end.on': True
            }
        }
        
        app = cherrypy.tree.mount(WebInterface(), '/', conf)
        cherrypy.tree.mount(UserInterface(), '/user')
        brdflix.ADMIN_INTERFACE = AdminInterface()
        cherrypy.tree.mount(brdflix.ADMIN_INTERFACE, '/admin')
        cherrypy.tree.mount(TestingGrounds(), '/tests')
        cherrypy.tree.mount(StreamInterface(), '/stream', stream_conf)
        cherrypy.tree.mount(WatchInterface(), '/watch')
        cherrypy.tree.mount(MovieInterface(), '/movies')
        cherrypy.tree.mount(TVInterface(), '/tv')
        cherrypy.tree.mount(ImageInterface(), '/img')
        brdflix.XBMC_INTERFACE = XBMCInterface()
        cherrypy.tree.mount(brdflix.XBMC_INTERFACE, '/xbmc')
        cherrypy.tree.mount(HLSInterface(), '/hls')
        cherrypy.tree.mount(SickBeardInterface(), '/sickbeard')
        cherrypy.tree.mount(ChartsInterface(), '/charts')
        cherrypy.tree.mount(DownloadInterface(), '/download')
        cherrypy.tree.mount(PublicInterface(), '/public')

        print "ATTEMPTING TO START CHERRYPY SERVER ON PORT", brdflix.PORT
        cherrypy.server.start()
        cherrypy.server.wait()
        print "NOW LISTENING ON PORT", brdflix.PORT

        perform_episode_check()

def perform_episode_check():
    # Check for new episodes
    brdflix.XBMC_INTERFACE.check_new()
    # Start the timer again
    brdflix.new_eps_timer = threading.Timer(brdflix.NEW_EPS_INTERVAL, perform_episode_check)
    brdflix.new_eps_timer.start()