import jsonrpclib
import urllib
import base64
from pprint import pprint
import time
import re
import urllib
import os
import subprocess
import cherrypy
from datetime import datetime

import brdflix
import settings
from datatypes import *
from helpers import *

def get_xbmc_server_url(external=False):
    x = settings.XBMC
    return "{0}://{1}:{2}@{3}:{4}".format(x.protocol, x.user, x.password, x.internal_host if not external else x.external_host, x.port)

def get_xbmc_jsonrpc_url():
    return "{0}/jsonrpc".format(get_xbmc_server_url(False))


def create_server_obj(retry_count=0, retry_max=1):
    try:
        server = jsonrpclib.Server(get_xbmc_jsonrpc_url())
        res = server.JSONRPC.Ping()
        return server
    except:
        if settings.XBMC.allow_start_process and retry_count < retry_max:
            attempt_start()
            return create_server_obj(retry_count + 1, retry_max)
        else:
            raise cherrypy.HTTPError(503)

def create_local_xbmc_server(x):
    url = "http://{0}:{1}@{2}:{3}/jsonrpc".format(x.username, x.password, x.host, int(x.port))
    print url
    server = jsonrpclib.Server(url)
    return server

def get_xbmc_image_url(path, external=False):
    # frodo
    if path.startswith("image:"):
        return "{0}/image/{1}".format(get_xbmc_server_url(external), urllib.quote(path.encode('utf-8'), ''))
    # eden (and before?)
    elif path.startswith("special:"):
        return "{0}/vfs/{1}".format(get_xbmc_server_url(external), urllib.quote(path.encode('utf-8'), ''))

class Episode:
    def __init__(self):
        self.id = ""
        self.idShow = ""
        self.season = 0
        self.episode = 0
        self.fname = ""
        self.file = ""
        self.showName = ""
        self.epName = ""
        self.summary = ""
        self.video = None
        self.watched = False
        self.resume = ""
        self.thumb_path = None
        self.firstaired = ""
        self.streams = StreamDetails()
        self.quality = "N/A"
        self.missing = False
        
    @property
    def thumbpath64(self):
        return "" if self.thumb_path is None else base64.b64encode(self.thumb_path)

    def __repr__(self):
        return "{0} - {1}x{2} - {3}".format(self.showName, self.season, str(self.episode).zfill(2), self.epName.encode('ascii', 'ignore'))
      
def getEpisodeInfo(episodeid):
    xbmc = create_server_obj()
    res = xbmc.VideoLibrary.GetEpisodeDetails(episodeid = int(episodeid), 
                                        properties = ['title', 'plot', 'thumbnail', 'playcount', 'episode', 'file', 'showtitle', 'resume', 'streamdetails', 'firstaired', 'tvshowid', 'season'])
    ep = Episode()
    item = res['episodedetails']
    ep = Episode()
    ep.id = episodeid
    ep.idShow = item['tvshowid']
    ep.season = item['season']
    ep.episode = item['episode']
    ep.file = item[u'file'].replace(u'\\', u'/')
    ep.showName = item['showtitle']
    ep.epName = item['title']
    ep.summary = item['plot']
    ep.resume = item['resume']
    ep.thumb_path = item['thumbnail']
    ep.watched = item['playcount'] is not None and int(item['playcount']) > 0
    tokens = ep.file.split('/')
    ep.fname = tokens[len(tokens)-1]
    if ep.thumb_path is None or ep.thumb_path == "":
        # fallback (currently frodo only, because of image://)
        ep.thumb_path = "image://" + urllib.quote(ep.file[:ep.file.rfind('.')] + ".tbn").replace('.', '%2e').replace('/', '%2f')
    if item['streamdetails'] is not None:
        ep.streams = StreamDetails(item['streamdetails'])
    ep.firstaired = item['firstaired']
    return ep

def getPreviousNextEpisodes(ep):
    prev = None
    next = None
    seasons = getSeasons(ep.idShow)
    seasonIndex = -1
    if seasons is not None and len(seasons) > 0:
        for si in range(len(seasons)):
            if int(seasons[si].num) == int(ep.season):
                seasonIndex = si
                break
    if seasonIndex != -1:
        eps = getEpisodes(ep.idShow, seasons[seasonIndex].num)
        epIndex = -1
        for ei in range(len(eps)):
            if int(eps[ei].id) == int(ep.id):
                epIndex = ei
                break
        if epIndex != -1:
            if epIndex != 0:
                prev = eps[epIndex-1]
            else:
                # this is the first episode of the season,
                # so try and get the last episode of the previous season
                if seasonIndex > 0:
                    prevSeason = seasons[seasonIndex-1]
                    prevEps = getEpisodes(ep.idShow, prevSeason.num)
                    if len(prevEps) > 0:
                        prev = prevEps[len(prevEps)-1]
            if epIndex < len(eps) - 1:
                next = eps[epIndex+1]
            else:
                # this is the last episode of the season,
                # so try and get the first episode of the next season
                if seasonIndex < len(seasons)-1:
                    nextSeason = seasons[seasonIndex+1]
                    nextEps = getEpisodes(ep.idShow, nextSeason.num)
                    if len(nextEps) > 0:
                        next = nextEps[0]
    return prev, next
        
def getEpisodes(idShow, season):
    eps = []
    xbmc = create_server_obj()
    res = xbmc.VideoLibrary.GetEpisodes(tvshowid = int(idShow), season = int(season), 
                                        properties = ['title', 'plot', 'thumbnail', 'playcount', 'episode', 'file', 'showtitle', 'resume', 'season', 'firstaired', 'dateadded'],
                                        sort={'order':'ascending', 'method':'episode'})
    
    for item in res['episodes']:
        ep = Episode()
        ep.id = item['episodeid']
        ep.idShow = idShow
        ep.season = item['season']
        ep.episode = item['episode']
        ep.file = item['file'].encode("ascii","ignore").replace('\\', '/')
        ep.showName = item['showtitle']
        ep.epName = item['title']
        ep.summary = item['plot']
        ep.resume = item['resume']
        ep.thumb_path = item['thumbnail']
        ep.watched = item['playcount'] is not None and int(item['playcount']) > 0
        tokens = ep.file.split('/')
        ep.fname = tokens[len(tokens)-1]
        ep.dateadded = datetime.fromtimestamp(time.mktime(time.strptime(item['dateadded'], "%Y-%m-%d %H:%M:%S"))) if item['dateadded'] is not None and item['dateadded'] != '' else None
        if ep.thumb_path is None or ep.thumb_path == "":
            # fallback (currently frodo only, because of image://)
            ep.thumb_path = "image://" + urllib.quote(ep.file[:ep.file.rfind('.')] + ".tbn").replace('.', '%2e').replace('/', '%2f')
        ep.firstaired = item['firstaired']
        eps.append(ep)
    return eps 
 
def getRecentEpisodes():
    eps = []
    xbmc = create_server_obj()
    res = xbmc.VideoLibrary.GetRecentlyAddedEpisodes(properties = ['tvshowid', 'season', 'title', 'plot', 'thumbnail', 'playcount', 'episode', 'file', 'showtitle', 'resume'])
    
    for item in res['episodes']:
        ep = Episode()
        ep.id = item['episodeid']
        ep.idShow = item['tvshowid']
        ep.season = item['season']
        ep.episode = item['episode']
        ep.file = item['file'].encode("ascii","ignore").replace('\\', '/')
        ep.showName = item['showtitle']
        ep.epName = item['title']
        ep.summary = item['plot']
        ep.resume = item['resume']
        ep.thumb_path = item['thumbnail']
        ep.watched = item['playcount'] is not None and int(item['playcount']) > 0
        tokens = ep.file.split('/')
        ep.fname = tokens[len(tokens)-1]
        if ep.thumb_path is None or ep.thumb_path == "":
            # fallback (currently frodo only, because of image://)
            ep.thumb_path = "image://" + urllib.quote(ep.file[:ep.file.rfind('.')] + ".tbn").replace('.', '%2e').replace('/', '%2f')                        
        eps.append(ep)
    return eps 
 
class Season:
    def __init__(self):
        self.idShow = ""
        self.num = 0
        self.showName = ""
        self.totalEps = 0
        self.watchedEps = 0
        self.thumb_path = None
        
    @property
    def watched(self):
        return self.watchedEps == self.totalEps
        
    @property
    def newEps(self):
        return self.totalEps - self.watchedEps
        
    @property
    def thumbpath64(self):
        return "" if self.thumb_path is None else base64.b64encode(self.thumb_path)
  
def getSeasons(idShow):
    seasons = []
    xbmc = create_server_obj()
    res = xbmc.VideoLibrary.GetSeasons(tvshowid = int(idShow), 
                                       properties = ['showtitle', 'thumbnail', 'watchedepisodes', 'episode', 'season'],
                                       sort={'order':'ascending', 'method':'episode'})
    if 'seasons' in res.keys():
        for item in res['seasons']:
            season = Season()
            season.idShow = idShow
            season.showName = item['showtitle']
            season.totalEps = item['episode']
            season.watchedEps = item['watchedepisodes']
            season.num = item['season']
            season.thumb_path = item['thumbnail']
            seasons.append(season)
    return seasons
    
class Show:
    def __init__(self):
        # base info
        self.id = ""
        self.name = ""
        self.totalEps = 0
        self.watchedEps = 0
        self.seasons = 0
        self.thumb_path = None
        self.folder = ""
        #extra info
        self.genre = ""
        self.year = ""
        self.rating = ""
        self.plot = ""
        self.studio = ""
        self.mpaa = ""
        self.imdbnumber = ""
        self.premiered = ""
        self.votes = ""
        self.fanart_path = "" 
        self.path = "" 
        self.sorttitle = ""
        self.genres = []
        self.tvdb_id = None
        
    @property
    def watched(self):
        return self.watchedEps == self.totalEps and self.totalEps > 0
        
    @property
    def newEps(self):
        return self.totalEps - self.watchedEps
        
    @property
    def thumbpath64(self):
        return "" if self.thumb_path is None else base64.b64encode(self.thumb_path)

    @property
    def fanart64(self):
        return "" if self.fanart_path is None else base64.b64encode(self.fanart_path)

    @property
    def is_user_favorite(self):
        user = getattr(cherrypy.request, 'user', None)
        if user is not None:
            res = FavoriteShow().query_one(user_id=user.id, xbmc_id=self.id)
            return res is not None
        return False
        
class ShowStats:
    def __init__(self):
        self.seasons = []
        self.eps = []
        self.last_watched = None
        self.newest = None
        self.first = None
        self.next = None
        
        
def getShowStats(idShow):
    stats = ShowStats()
    stats.seasons = getSeasons(idShow)
    stats.eps = []
    for season in stats.seasons:
        stats.eps.extend(getEpisodes(idShow, season.num))
    if len(stats.eps) > 0:
        stats.first = stats.eps[0]
        stats.newest = stats.eps[len(stats.eps)-1]
        for ep in reversed(stats.eps):
            if ep.watched:
                stats.last_watched = ep
                break
        index = -1 if stats.last_watched is None else stats.eps.index(stats.last_watched)
        if index != -1 and index < len(stats.eps) - 1:
            stats.next = stats.eps[index + 1]
        else:
            for ep in stats.eps:
                if not ep.watched:
                    stats.next = ep
                    break
    return stats
        
def getNextEpisode(idShow):
    seasons = getSeasons(idShow)
    seasons.reverse()
    for s in seasons:
        if s.totalEps > s.watchedEps:
            eps = getEpisodes(idShow, s.num)
            for ep in eps:
                if not ep.watched:
                    return ep
    return None
            
def getShowInfo(idShow):
    xbmc = create_server_obj()
    res = xbmc.VideoLibrary.GetTVShowDetails(tvshowid=int(idShow), properties = ['thumbnail', 'watchedepisodes', 'episode',
                                                                                 'season', 'file', 'genre', 'imdbnumber', 'fanart',
                                                                                 'plot'])
    show = Show()
    item = res['tvshowdetails']
    show.id = item['tvshowid']
    show.name = item['label']
    show.tvdb_id = item['imdbnumber']
    show.totalEps = item['episode']
    show.watchedEps = item['watchedepisodes']
    show.seasons = item['season']
    show.thumb_path = item['thumbnail']
    show.path = item['file'].encode("ascii","ignore").strip('/')
    show.folder = show.path[show.path.rfind('/')+1:]
    if type(item['genre']) is list:
        show.genres = item['genre']
    else:
        show.genres = item['genre'].split(' / ')
    show.fanart_path = item['fanart']
    show.plot = item['plot']
    return show

def getShowPoster(idShow):
    xbmc = create_server_obj()
    res = xbmc.VideoLibrary.GetTVShowDetails(tvshowid=int(idShow), properties = ['thumbnail'])
    return res['tvshowdetails']['thumbnail']
        
def getShowTVDB_ID(idShow):
    xbmc = create_server_obj()
    res = xbmc.VideoLibrary.GetTVShowDetails(tvshowid=int(idShow), properties = ['imdbnumber'])
    return res['tvshowdetails']['imdbnumber']
        
def getShows(ascending="True", sort_method="label", ignorearticle="True"):
    shows = []
    xbmc = create_server_obj()
    res = xbmc.VideoLibrary.GetTVShows(properties = ['thumbnail', 'watchedepisodes', 'episode', 'season', 'file', 'genre',
                                                     'imdbnumber'],
                                       sort={'order':'ascending' if ascending == "True" else "descending", 
                                            'method': sort_method, 
                                            'ignorearticle': ignorearticle == "True"})
    for item in res['tvshows']:
        show = Show()
        show.id = item['tvshowid']
        show.name = item['label']
        show.totalEps = item['episode']
        show.watchedEps = item['watchedepisodes']
        show.seasons = item['season']
        show.thumb_path = item['thumbnail']
        show.path = item['file'].encode("ascii","ignore").replace('\\', '/').strip('/')
        show.folder = show.path[show.path.rfind('/')+1:]
        if type(item['genre']) is list:
            show.genres = item['genre']
        else:
            show.genres = item['genre'].split(' / ')
        show.tvdb_id = item['imdbnumber']
        shows.append(show)
    return shows

class StreamDetails:
    def __init__(self, js=None):
        self.audio = None
        self.video = None
        if js is not None:
            self.deserialize(js)
    
    def deserialize(self, js):
        if 'audio' in js:
            self.audio = []
            for a in js['audio']:
                self.audio.append(AudioStream(a))
        if 'video' in js:
            self.video = []
            for v in js['video']:
                self.video.append(VideoStream(v))

    @property
    def video_quality(self):
        if self.video is None:
            return None
        width = self.video[0].width
        if width == 1920:
            return "1080p"
        elif width == 1280:
            return "720p"
        elif width == 640:
            return "SD"
        return None
        
    @property
    def audio_quality(self):
        ac = self.audio_channels
        val = ""
        if ac == 8:
            val = "7.1"
        elif ac == 6:
            val = "5.1"
        elif ac == 3:
            val = "2.1"
        elif ac == 2:
            val = "Stereo"
        elif ac == 1:
            val = "Mono"
        if self.audio_codec == "dca":
            val = val + " DTS"
        return val
        
    @property
    def audio_channels(self):
        return None if self.audio is None else self.audio[0].channels
        
    @property
    def audio_codec(self):
        return None if self.audio is None else self.audio[0].codec
        
    @property
    def video_codec(self):
        return None if self.video is None else self.video[0].codec
        
    @property
    def eng_track(self):
        if self.audio is not None:
            for i in range(len(self.audio)):
                if self.audio[i].lang == 'eng':
                    return i
        return None
    
class VideoStream:
    def __init__(self, js=None):
        self.codec = ""
        self.duration = 0
        self.width = 0
        self.height = 0
        self.aspect = 0.0
        if js is not None:
            self.deserialize(js)
    
    def deserialize(self, js):
        self.codec = js['codec']
        self.duration = int(js['duration'])
        self.width = int(js['width'])
        self.height = int(js['height'])
        self.aspect = float(js['aspect'])

class AudioStream:
    def __init__(self, js=None):
        self.codec = ""
        self.lang = ""
        self.channels = 0
        if js is not None:
            self.deserialize(js)
    
    def deserialize(self, js):
        self.codec = js['codec']
        self.lang = js['language']
        self.channels = int(js['channels'])
    
class Movie:
    def __init__(self):
        self.id = ""
        self.name = ""
        self.year = ""
        self.folder = ""
        self.fname = ""
        self.file = ""
        self.video = None
        self.trailer_fname = ""
        self.trailer_file = ""
        self.trailer_video = None
        self.watched = False
        self.trailer_youtube_id = ""
        self.summary = ""
        self.rating = ""
        self.thumb_path = None
        self.fanart = None
        self.quality = None
        self.audio_quality = None
        self.audio_channels = None
        self.streams = StreamDetails()
        self.genres = []
        
    @property
    def thumbpath64(self):
        return "" if self.thumb_path is None else base64.b64encode(self.thumb_path)
        
    @property
    def fanart64(self):
        return "" if self.fanart is None else base64.b64encode(self.fanart)

    @property
    def is_user_watchlist(self):
        user = getattr(cherrypy.request, 'user', None)
        if user is not None:
            res = WatchlistItem().query_one(user_id=user.id, xbmc_id=self.id)
            return res is not None
        return False

def getAllUniqueGenres(items):
    genres = []
    for item in items:
        for genre in item.genres:
            if not genre in genres and genre.strip() != "":
                genres.append(genre)
    return sorted(genres)
        
def filterMoviesByGenres(movies, genres=[], any=True):
    m = []
    for movie in movies:
        count = 0
        for genre in movie.genres:
            if genre in genres:
                count = count + 1
                if any: break
        if count == len(genres) or (any and count > 0):
            m.append(movie)
    return m
        
def getMovies(ascending="True", sort_method="label", ignorearticle="True"):
    xbmc = create_server_obj()
    res = xbmc.VideoLibrary.GetMovies(properties = ['thumbnail', 'playcount', 'rating', 'streamdetails', 'genre', 'year'], 
                                      sort={'order':'ascending' if ascending == "True" else "descending", 
                                            'method': sort_method, 
                                            'ignorearticle': ignorearticle == "True"})
    return parseMovieResults(res)
    
def getRecentMovies(ascending="True", sort_method="label", ignorearticle="True"):
    xbmc = create_server_obj()
    res = xbmc.VideoLibrary.GetRecentlyAddedMovies(properties = ['thumbnail', 'playcount', 'rating', 'streamdetails', 'genre', 'year'])
    return parseMovieResults(res)

def parseMovieResults(res):
    movies = []
    for item in res['movies']:
        movie = Movie()
        movie.id = item['movieid']
        movie.year = item['year']
        movie.name = item['label']
        movie.watched = item['playcount'] is not None and int(item['playcount']) > 0
        movie.thumb_path = item['thumbnail']
        movie.rating = round(float(item['rating']), 1)
        if type(item['genre']) is list:
            movie.genres = item['genre']
        else:
            movie.genres = item['genre'].split(' / ')
        # movie.file = item['file'].encode("ascii","ignore").replace('\\', '/')
        # tokens = movie.file.split('/')
        # movie.fname = tokens[len(tokens)-1]
        # movie.folder = tokens[len(tokens)-2]      
        if item['streamdetails'] is not None:
            movie.streams = StreamDetails(item['streamdetails'])
            et = movie.streams.eng_track
            #if et is not None and et != 0:
                #print movie.name + ':', et
                #pprint(item['streamdetails']['audio'])
        movies.append(movie)
    return movies    
    
def getMovieInfo(id):
    xbmc = create_server_obj()
    res = xbmc.VideoLibrary.GetMovieDetails(movieid=int(id), properties = ['title', 'thumbnail', 'playcount', 'fanart', 'file', 'trailer', 'plot', 'rating', 'streamdetails'])

    item = res['moviedetails']
    movie = Movie()
    movie.id = id
    movie.name = item['title']
    movie.file = item['file'].encode("ascii","ignore").replace('\\', '/')
    tokens = movie.file.split('/')
    movie.folder = tokens[len(tokens)-2]
    movie.fname = tokens[len(tokens)-1]
    movie.watched = item['playcount'] is not None and int(item['playcount']) > 0
    movie.summary = item['plot']
    movie.thumb_path = item['thumbnail']
    movie.fanart = item['fanart']
    tf = item['trailer']
    movie.trailer_file = item['trailer']
    if tf is not None and tf != "" and not tf.startswith('plugin://'):
        tf = tf[tf.rfind('/')+1:]
    movie.trailer_fname = tf
    movie.rating = item['rating']
    
    if tf.startswith('plugin://plugin.video.youtube'):
        movie.trailer_youtube_id = tf.replace('plugin://plugin.video.youtube/?action=play_video&videoid=', '')
    
    return movie
    
def performScan(folder=None):
    xbmc = create_server_obj()
    if folder is not None:
        res = xbmc.VideoLibrary.Scan(directory=folder)
    else:
        res = xbmc.VideoLibrary.Scan()
    print "XBMC Library Scan: ", res
    return res


# { "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": 200 }, "options":{ "resume": false } }, "id": 1 }
def playEpisode(server, episodeid):
    xbmc = create_local_xbmc_server(server)
    xbmc.Player.Open(item={ 'episodeid': int(episodeid) }, options={ 'resume': False })

def setFullscreen(server, fullscreen):
    xbmc = create_local_xbmc_server(server)
    xbmc.GUI.SetFullscreen(fullscreen=fullscreen)

def setMovieWatched(movieid, watched=True):
    xbmc = create_server_obj()
    if watched:
        res = xbmc.VideoLibrary.SetMovieDetails(movieid=int(movieid), playcount=1, lastplayed=time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", time.gmtime()))
    else:
        res = xbmc.VideoLibrary.SetMovieDetails(movieid=int(movieid), playcount=0)
    print "XBMC Set Moive Watched Status: ", res
    return res
    
def setEpisodeWatched(episodeid, watched=True):
    xbmc = create_server_obj()
    if watched:
        res = xbmc.VideoLibrary.SetEpisodeDetails(episodeid=int(episodeid), playcount=1, lastplayed=time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", time.gmtime()))
    else:
        res = xbmc.VideoLibrary.SetEpisodeDetails(episodeid=int(episodeid), playcount=0)
    print "XBMC Set Episode Watched Status: ", res
    return res
    
def getLocalPathFromPath64(path64):
    fullname = base64.b64decode(path64).decode('utf-8')
    if fullname.startswith('\\'):
        fname = re.sub(r'//[^/]+/([A-Z])\$*/', r'\1:/', fullname.replace('\\', '/'))
    else:
        fname = re.sub(r'smb://[^/]+/([A-Z])\$*/', r'\1:/', fullname.replace('\\', '/'))


    # TODO: Fix this!

    # HACK: ALERT!
    fname = fname.replace("smb://<TODO>/TV Shows/", "S:/TV Shows/")
    # HACK: ALERT!
    fname = fname.replace("smb://<TODO>/Movies/", "Z:/Movies/")

    return fname

def getLocalPathFromPath64Image(path64):
    path = base64.b64decode(path64)
    path = path.replace('image://', '').replace('special://', '')
    path = urllib.unquote(path)
    return getLocalPathFromPath64(base64.b64encode(path))
    
def attempt_start(sleep_wait=None):
    fname = settings.XBMC.filename
    if fname is not None and os.path.isfile(fname):
        print "Attempting to start XBMC on host system!"
        try:
            subprocess.Popen(fname)
            time.sleep(settings.XBMC.start_wait_seconds if sleep_wait is None else sleep_wait)
        except:
            print "ERROR: Unable to start XBMC process on host system!"
    
 