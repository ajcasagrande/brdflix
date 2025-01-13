import cherrypy

from helpers import *
from datatypes import *

class DownloadInterface(object):

    _cp_config = { 'tools.log_request.on': True,
                   'tools.login_required.on': True }

    @cherrypy.expose
    def index(self, **kwargs):
        if not cherrypy.request.user.group.download_rights:
            return "Download Denied!"
        media = Media().from_id(kwargs.get('media_id', None))
        if media is not None:
            if 'submit' in kwargs:
                # Redirect based on what the user chose
                if kwargs['type'] == 'raw':
                    url = "/download/raw?media_id={0}".format(media.id)
                    raise cherrypy.HTTPRedirect(url)
                elif kwargs['type'] == 'transcode':
                    url = "/download/transcode?media_id={0}&format={1}&volume={2}&quality={3}".format(media.id, kwargs['format'], kwargs['vol'], kwargs['quality'])
                    raise cherrypy.HTTPRedirect(url)
            else:
                t, j = get_jinja_template('forms/download_form.html')
                j.media = media
                # Determine the human readable size of the file for raw downloading
                raw = j.media.bytes / 1024.0 / 1024.0
                if raw < 1000:
                    j.raw_size = "{0} MB".format(int(round(raw)))
                else:
                    j.raw_size = "{0} GB".format(round(raw / 1024.0, 2))
                j.max_quality_id = j.user.group.max_quality_id
                j.max_quality = Quality().from_id(j.max_quality_id)
                if j.max_quality is None:
                    j.qualities = Quality().query_all()
                else:
                    j.qualities = []
                    for qual in Quality().query_all():
                        if qual.sort_index <= j.max_quality.sort_index:
                            j.qualities.append(qual)
                j.embed = kwargs.get('embed', 'False') == 'True'
                return t.render(j.kwargs())

    @cherrypy.expose
    def raw(self, media_id):
        # Will redirect locally if a local user
        url = '{0}/stream/raw_download?media_id={1}'.format(get_stream_host(), media_id)
        #raise cherrypy.HTTPRedirect(url)
        t, j = get_jinja_template("transcode_download.html")
        j.url = url
        return t.render(j.kwargs())

    @cherrypy.expose
    def transcode(self, media_id, format='flv', volume=256, quality=0):
        # Will redirect locally if a local user
        url = '{0}/stream/transcode_download?media_id={1}&format={2}&volume={3}&quality={4}'.format(get_stream_host(), media_id, format, volume, quality)
        #raise cherrypy.HTTPRedirect(url)
        t, j = get_jinja_template("transcode_download.html")
        j.url = url
        return t.render(j.kwargs())


