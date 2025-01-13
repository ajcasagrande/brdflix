import cherrypy
import os
import urllib
import base64
import time
import hashlib
from PIL import Image, ImageDraw, ImageFont, ImageFile
from cStringIO import StringIO
from datetime import datetime, timedelta
from pprint import pprint

from helpers import *
from decorators import *
from db_mysql import DEFAULT as db
from datatypes import *
import brdflix
import xbmc
from transcode import *
import settings

# Do this to prevent errors when loading large images
ImageFile.MAXBLOCK = 2**20

class ImageInterface:
    _cp_config = { 'tools.log_request.on': False,
                   'tools.login_required.on': False }

    # GLOBAL IMAGES / FONTS
    _OVERLAY_FONT = ImageFont.truetype("arial.ttf", 10)

    # Do not load this as image... otherwise text will constantly get overwritten on it
    _CIRCLE = "circle_24.png"

    _OVERLAY_WATCHED_45 = Image.open(os.path.join(brdflix.IMAGES_DIR, "OverlayWatched_45.png"), 'r')

    @cherrypy.expose
    def episodeThumb(self, season, episode, watched=False, new=False, thumbpath64="", w=None, h=None):
        cherrypy.response.headers['Content-Type'] = 'image/jpeg'

        if w is None and h is None:
            # defaults
            w = 200
            h = 112

        watched = watched == 'True' or watched == '1' or watched == 'true'
        isMissing = thumbpath64 is None or thumbpath64 == ""

        if not isMissing:
            cache_id = hashlib.sha256("{0}_{1}_{2}_{3}_{4}_{5}_{6}".format(watched, season, episode, new, thumbpath64, w, h)).hexdigest()
            cache_fname = get_generic_cache_fullname(cache_id, '.jpg')

            row = db.fetch_one('select * from image_cache where id = %s', (cache_id,))
            cache = db.get_generic(ImageCache(), row)

            if_mod_since = cherrypy.request.headers.get('If-Modified-Since',  None)
            if cache is not None and if_mod_since is not None:
                try:
                    if_mod = gmtime_for_str(if_mod_since)
                    last_mod = gmtime_for_datetime(cache.last_updated)
                    if last_mod <= if_mod:
                        raise cherrypy.HTTPRedirect('/304', 304)
                except ValueError:
                    pass

            if cache is not None and os.path.isfile(cache.fname) and (datetime.now() - cache.last_updated).days < settings.GLOBAL.max_image_cache_days:
                img = Image.open(cache.fname)
                buffer = StringIO()
                img.save(buffer, 'JPEG', quality=85, optimize=True)
                output = buffer.getvalue()
                buffer.close()
                del img
                try:
                    cherrypy.response.headers['Last-Modified'] = gmt_timestamp_for_datetime(cache.last_updated)
                except AttributeError:
                    pass
                return output

        if isMissing:
            img = Image.open(os.path.join(brdflix.IMAGES_DIR, "DefaultVideoCover.png"))
        else:
            url = xbmc.get_xbmc_image_url(base64.b64decode(thumbpath64))
            io = StringIO(urllib.urlopen(url).read())
            try:
                img = Image.open(io)
            except IOError:
                io.close()
                isMissing = True
                exts = ['.mkv', '.avi', '.mp4', '.wmv', '.mov' ]
                fname = xbmc.getLocalPathFromPath64Image(thumbpath64).replace('video@', '').rstrip('/').rstrip()
                for ext in exts:
                    fname = fname.replace(ext, ".tbn")
                if fname.endswith('.tbn') and os.path.isfile(fname):
                    img = Image.open(fname)
                    isMissing = False
                else:
                    for ext in exts:
                        vid_file = fname.replace('.tbn', ext)
                        if os.path.isfile(vid_file):
                            fname = vid_file.replace(ext, '.tbn')
                            break
                    if os.path.isfile(vid_file):
                        print "Attempting to generate episode thumb for future use."
                        print '"{0}"'.format(fname)
                        #return generate_thumb(base64.b64encode(vid_file))
                        res = generate_thumb(base64.b64encode(vid_file))
                        try:
                            io = StringIO(res)
                            img = Image.open(io)
                            isMissing = False
                            if fname.endswith('.tbn'):
                                img.save(fname, 'JPEG', quality=85, optimize=True)
                        except IOError:
                            isMissing = True
                if isMissing:
                    img = Image.open(os.path.join(brdflix.IMAGES_DIR, "DefaultVideoCover.png"))

        if w is not None or h is not None:
            ratio = 1.0 * img.size[0] / img.size[1]
            if w is None:
                w = round(float(h) * ratio)
            elif h is None:
                h = round(float(w) / ratio)
            img = img.resize((int(w), int(h)), Image.ANTIALIAS)
        
        if watched:
            wo = Image.open(os.path.join(brdflix.IMAGES_DIR, "OverlayWatched.png"), 'r')
            wo = wo.resize((45, 45), Image.ANTIALIAS)
            img.paste(wo, (int(w) - 45, 0), wo)
            del wo
        
        # bb = Image.open(os.path.join(brdflix.IMAGES_DIR, "bottom_bar.png"), 'r')
        # bb = bb.resize((200, 16), Image.ANTIALIAS)
        # sfont = ImageFont.truetype("arial.ttf", 12)
        # stext = u"{0}x{1} - {2}".format(season, episode.zfill(2), epName)
        # sdraw = ImageDraw.Draw(bb)
        # (stw, sth) = sdraw.textsize(stext, font=sfont)
        # sdraw.text((3, 1), stext, fill=(255,255,255), font=sfont)
        # img.paste(bb, (0, img.size[1]-bb.size[1]), bb)

        buffer = StringIO()
        img.save(buffer, 'JPEG', quality=85, optimize=True)
        if not isMissing:
            cache = ImageCache()
            cache.path64 = thumbpath64
            cache.w = w
            cache.h = h
            cache.type = 'EPISODE'
            cache.fname = cache_fname
            cache.id = cache_id
            save_to_cache(img, cache, 'JPEG')
        output = buffer.getvalue()
        buffer.close()
        del img
        if io:
            io.close()
        return output
    
    @cherrypy.expose
    def xbmcShowPoster(self, id, w=None, h=None):
        path64 = base64.b64encode(xbmc.getShowPoster(id))
        return self.xbmcImage(path64, w, h, "TVSHOW")
    
    @cherrypy.expose
    def xbmcImage(self, path64, w=None, h=None, type=None):
        cherrypy.response.headers['Content-Type'] = 'image/jpeg'

        cache_fname = get_cache_fullname(path64, w, h, type)
        cache_id = hashlib.sha256(cache_fname).hexdigest()

        row = db.fetch_one('select * from image_cache where id = %s', (cache_id,))
        cache = db.get_generic(ImageCache(), row)
        
        if_mod_since = cherrypy.request.headers.get('If-Modified-Since',  None)
        if cache is not None and if_mod_since is not None:
            try:
                if_mod = gmtime_for_str(if_mod_since)
                last_mod = gmtime_for_datetime(cache.last_updated)
                if last_mod <= if_mod:
                    raise cherrypy.HTTPRedirect('/304', 304)
            except ValueError:
                pass

        if cache is not None and os.path.isfile(cache.fname) and (datetime.now() - cache.last_updated).days < settings.GLOBAL.max_image_cache_days:
            img = Image.open(cache.fname)
            buffer = StringIO()
            img.save(buffer, 'JPEG', quality=85, optimize=True)
            output = buffer.getvalue()
            buffer.close()
            del img
            try:
                cherrypy.response.headers['Last-Modified'] = gmt_timestamp_for_datetime(cache.last_updated)
            except AttributeError:
                pass
            return output

        cache = ImageCache()
        cache.path64 = path64
        cache.w = w
        cache.h = h
        cache.type = type
        cache.fname = cache_fname
        cache.id = cache_id

        url = xbmc.get_xbmc_image_url(base64.b64decode(path64))
        bad = False
        try:
            io = StringIO(urllib.urlopen(url).read())
        except:
            bad = True
        if not bad and w is None and h is None:
            output = io.getvalue()
            try:
                img = Image.open(io)
                save_to_cache(img, cache, 'JPEG')
                del img
                io.close()
                return output
            except:
                bad = True
        if bad or w is not None or h is not None:
            if not bad:
                try:
                    img = Image.open(io)
                except:
                    bad = True
            if bad:
                fname = "poster_120.jpg"
                if type == "MOVIE" or type == "TVSHOW":
                    fname = "poster_120.jpg"
                elif type == "EPISODE":
                    fname = "episode_200.jpg"
                img = Image.open(os.path.join(brdflix.IMAGES_DIR, fname))

            if w is not None or h is not None:
                ratio = 1.0 * img.size[0] / img.size[1]
                if w is None:
                    w = round(float(h) * ratio)
                elif h is None:
                    h = round(float(w) / ratio)
                if type == "TVSHOW" and img.size[0] > img.size[1]:
                    h = round(float(w) / ratio)
                img = img.resize((int(w), int(h)), Image.ANTIALIAS)
            save_to_cache(img, cache, 'JPEG')
            buffer = StringIO()
            img.save(buffer, 'JPEG', quality=85, optimize=True)
            output = buffer.getvalue()
            buffer.close()
            del img
            try:
                cherrypy.response.headers['Last-Modified'] = gmt_timestamp_for_datetime(cache.last_updated)
            except AttributeError:
                pass
            return output
    
    @cherrypy.expose
    def tvshowOverlay(self, watched=False, new=False, newCount=-1, w=120, h=180):
        cache_id = hashlib.sha256("{0}_{1}_{2}_{3}_{4}".format(watched, new, newCount, w, h)).hexdigest()
        cache_fname = get_generic_cache_fullname(cache_id, '.png')

        row = db.fetch_one('select * from image_cache where id = %s', (cache_id,))
        cache = db.get_generic(ImageCache(), row)

        if_mod_since = cherrypy.request.headers.get('If-Modified-Since',  None)
        if cache is not None and if_mod_since is not None:
            try:
                if_mod = gmtime_for_str(if_mod_since)
                last_mod = gmtime_for_datetime(cache.last_updated)
                if last_mod <= if_mod:
                    raise cherrypy.HTTPRedirect('/304', 304)
            except ValueError:
                pass

        if cache is not None and os.path.isfile(cache.fname) and (datetime.now() - cache.last_updated).days < settings.GLOBAL.max_image_cache_days:
            img = Image.open(cache.fname)
            buffer = StringIO()
            img.save(buffer, 'PNG', optimize=True)
            output = buffer.getvalue()
            buffer.close()
            del img
            try:
                cherrypy.response.headers['Last-Modified'] = gmt_timestamp_for_datetime(cache.last_updated)
            except AttributeError:
                pass
            return output

        bg = Image.new('RGBA', (int(w), int(h)), (255, 255, 255, 0))
        
        if watched == 'True' or watched == '1' or watched == 'true':
            bg.paste(self._OVERLAY_WATCHED_45, (int(w) - self._OVERLAY_WATCHED_45.size[0], 0), self._OVERLAY_WATCHED_45)
        
        if int(newCount) > 0:
            circle = Image.open(os.path.join(brdflix.IMAGES_DIR, self._CIRCLE), 'r')
            r = circle.size[0] / 2
            draw = ImageDraw.Draw(circle)

            (tw, th) = draw.textsize(str(newCount), font=self._OVERLAY_FONT)
            draw.text((r-(0.5*tw), 7), str(newCount), fill=(0,0,0), font=self._OVERLAY_FONT)
            bg.paste(circle, (5, 5), circle)

        cache = ImageCache()
        cache.w = w
        cache.h = h
        cache.type = 'TVSHOW_OVERLAY'
        cache.fname = cache_fname
        cache.id = cache_id
        cache.path64 = None

        buffer = StringIO()
        bg.save(buffer, 'PNG', optimize=True)
        save_to_cache(bg, cache, 'PNG')
        cherrypy.response.headers['Content-Type'] = 'image/png'
        output = buffer.getvalue()
        buffer.close()
        del bg
        return output
        
    @cherrypy.expose
    def movieOverlay(self, watched=False, new=False, rating=None, w=120, h=180):
        cache_id = hashlib.sha256("{0}_{1}_{2}_{3}_{4}".format(watched, new, rating, w, h)).hexdigest()
        cache_fname = get_generic_cache_fullname(cache_id, '.png')

        row = db.fetch_one('select * from image_cache where id = %s', (cache_id,))
        cache = db.get_generic(ImageCache(), row)

        if_mod_since = cherrypy.request.headers.get('If-Modified-Since',  None)
        if cache is not None and if_mod_since is not None:
            try:
                if_mod = gmtime_for_str(if_mod_since)
                last_mod = gmtime_for_datetime(cache.last_updated)
                if last_mod <= if_mod:
                    raise cherrypy.HTTPRedirect('/304', 304)
            except ValueError:
                pass

        if cache is not None and os.path.isfile(cache.fname) and (datetime.now() - cache.last_updated).days < settings.GLOBAL.max_image_cache_days:
            img = Image.open(cache.fname)
            buffer = StringIO()
            img.save(buffer, 'PNG', optimize=True)
            output = buffer.getvalue()
            buffer.close()
            del img
            try:
                cherrypy.response.headers['Last-Modified'] = gmt_timestamp_for_datetime(cache.last_updated)
            except AttributeError:
                pass
            return output

        bg = Image.new('RGBA', (int(w), int(h)), (255, 255, 255, 0))
        
        if watched == 'True' or watched == '1' or watched == 'true':
            bg.paste(self._OVERLAY_WATCHED_45, (int(w) - self._OVERLAY_WATCHED_45.size[0], 0), self._OVERLAY_WATCHED_45)
        
        if rating is not None:
            circle = Image.open(os.path.join(brdflix.IMAGES_DIR, self._CIRCLE), 'r')
            rating = round(float(rating), 1)
            r = circle.size[0] / 2
            draw = ImageDraw.Draw(circle)

            (tw, th) = draw.textsize(str(rating), font=self._OVERLAY_FONT)
            draw.text((r-(0.5*tw), 7), str(rating), fill=(0,0,0), font=self._OVERLAY_FONT)
            bg.paste(circle, (5, 5), circle)

        cache = ImageCache()
        cache.w = w
        cache.h = h
        cache.type = 'MOVIE_OVERLAY'
        cache.fname = cache_fname
        cache.id = cache_id
        cache.path64 = None

        buffer = StringIO()
        bg.save(buffer, 'PNG', optimize=True)
        save_to_cache(bg, cache, 'PNG')
        cherrypy.response.headers['Content-Type'] = 'image/png'
        output = buffer.getvalue()
        buffer.close()
        del bg
        return output


def save_to_cache(img, cache, format='JPEG'):
    if format == 'JPEG':
        img.save(cache.fname, 'JPEG', quality=85, optimize=True)
    elif format == 'PNG':
        img.save(cache.fname, 'PNG', optimize=True)
    cache.last_updated = datetime.now()
    db.insert_or_update_generic(cache)

def get_cache_fullname(path64, w, h, type):
    fname = hashlib.sha256("{0}_{1}_{2}".format(path64, w, h)).hexdigest() + '.jpg'
    path = os.path.join(settings.GLOBAL.image_cache_dir, fname[:1])
    if not os.path.exists(path):
        os.makedirs(path)
    return os.path.join(path, fname).replace('\\', '/')

def get_generic_cache_fullname(sha256, ext):
    fname = sha256 + ext
    path = os.path.join(settings.GLOBAL.image_cache_dir, fname[:1])
    if not os.path.exists(path):
        os.makedirs(path)
    return os.path.join(path, fname).replace('\\', '/')

def generate_thumb(path64, offset=100, width=-1, height=-1, outname=None):
    p = TranscodeProcess()
    p.fname = xbmc.getLocalPathFromPath64(path64)
    p.offset = offset
    p.width = width
    p.height = height
    if width == -1:
        p.setup('gen_thumb')
    else:
        p.setup('thumb')
    
    p.run()
    raw = p.process.communicate()[0]
    # delete the process to clean up handles
    del p.process

    io = StringIO(raw)
    try:
        img = Image.open(io)
        buffer = StringIO()
        img.save(buffer, 'JPEG', quality=85, optimize=True)
        if outname:
            img.save(outname, 'JPEG', quality=85, optimize=True)
        res = buffer.getvalue()
        buffer.close()
        del img
        #print "Final transfer size: {0} KB".format(stream.transfer_size / 1024.0)
        return res
    except IOError:
        return None
