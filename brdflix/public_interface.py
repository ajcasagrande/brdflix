import cherrypy
from pprint import pprint

import brdflix
from datatypes import *
from helpers import *

class PublicInterface(object):
    _cp_config = { 'tools.log_request.on': True,
                   'tools.login_required.on': False }

    @cherrypy.expose
    def watch(self, guid):
        link = PublicLink().from_id(guid)
        if link is not None:
            t, j = get_jinja_template("public_video.html")
            #j.stream_host = 'http://{0}:{1}'.format(brdflix.LAN_IP if cherrypy.request.is_local else brdflix.EXTERNAL_IP, brdflix.PORT)
            j.stream_host = ''
            j.media = Media().from_id(link.media_id)
            j.link = link
            #pprint(link.__dict__)
            return t.render(j.kwargs())
        else:
            raise cherrypy.HTTPError(404)

