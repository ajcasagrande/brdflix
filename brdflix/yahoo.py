import urllib
import urllib2
import os
import base64
from threading import Thread

import xbmc

def download_trailer(movie, wait=False):
    fullname = xbmc.getLocalPathFromPath64(base64.b64encode(movie.file))
    folder = fullname[:fullname.lower().rfind('/')]
    url = movie.trailer_file
    if os.path.exists(folder):
        outfile = os.path.join(folder, 'movie-trailer.mov')
        print "Downloading Trailer:"
        print url
        print outfile
        if wait:
            urllib.urlretrieve(url, outfile)
        else:
            thread = Thread(target=urllib.urlretrieve, args=[url, outfile])
            thread.daemon = True
            thread.start()
