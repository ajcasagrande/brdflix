from BeautifulSoup import BeautifulSoup
from pprint import pprint
import urllib2

import brdflix
import settings

class Video:
    def __init__(self):
        self.filename = ""
        self.id = ""
        self.duration = 0
        
class NowPlayingEntry:
    def __init__(self):
        self.id = 0
        self.title = ""
        #self.album = ""
        #self.artist = ""
        self.duration = 0
        #self.bitrate = 0
        self.size = 0
        self.path = ""
        self.username = ""
        self.playerid = 0
        self.playername = ""
        self.minutesago = 0

def get_xml(url):
    try:
        request = urllib2.Request(url)
        request.add_header("User-Agent", "Mozilla/5.001 (windows; U; NT4.0; en-US; rv:1.0) Gecko/25250101")
        xml = urllib2.urlopen(request).read()
        return xml
    except:
        print "Error accessing:", url
        return None

def getSubsonicLoginUrl(username, password):
    return "http://{0}:{1}/rest/ping.view?u={2}&p={3}&v=1.8.0&c=brdflix".format(settings.SUBSONIC.internal_host, settings.SUBSONIC.port, username, password)
        
def getSubsonicUrl(command, sonic_user, sonic_pass, **kwargs):
    url = "http://{0}:{1}/rest/{2}.view?u={3}&p={4}&v=1.8.0&c=brdflix".format(settings.SUBSONIC.internal_host, settings.SUBSONIC.port, command, sonic_user, sonic_pass)
    for key in kwargs:
        url = "{0}&{1}={2}".format(url, key, kwargs[key])
    return url

def getSubsonicMovieId(movieFolder, sonic_user, sonic_pass):
    url = getSubsonicUrl("getIndexes", sonic_user, sonic_pass, musicFolderId=2)
    xml = get_xml(url)
    soup = BeautifulSoup(xml)
    artist = soup.find("artist", attrs = { "name" : movieFolder })
    if artist:
        return artist['id']
    return None    
    
def getSubsonicShowId(showFolder, sonic_user, sonic_pass):
    url = getSubsonicUrl("getIndexes", sonic_user, sonic_pass, musicFolderId=1)
    xml = get_xml(url)
    soup = BeautifulSoup(xml)
    artist = soup.find("artist", attrs = { "name" : showFolder })
    if artist:
        return artist['id']
    return None
    
def getSubsonicFolderId(parent_id, folderName, sonic_user, sonic_pass):
    url = getSubsonicUrl("getMusicDirectory", sonic_user, sonic_pass, id=parent_id)
    xml = get_xml(url)
    soup = BeautifulSoup(xml)
    child = soup.find("child", title=folderName)
    if child:
        return child['id']
    return None
    
def getSubsonicSeasonId(showFolder, seasonFolder, sonic_user, sonic_pass):
    show_id = getSubsonicShowId(showFolder, sonic_user, sonic_pass)
    if show_id:
        return getSubsonicFolderId(show_id, seasonFolder, sonic_user, sonic_pass)
    return None    

def getSubsonicVideos(folderId, sonic_user, sonic_pass):
    url = getSubsonicUrl("getMusicDirectory", sonic_user, sonic_pass, id=folderId)
    xml = get_xml(url)
    soup = BeautifulSoup(xml)
    vids = []
    childs = soup.findAll("child", isvideo="true")
    for child in childs:
        vid = Video()
        vid.filename = child['path'][child['path'].rfind('/')+1:]
        vid.id = child['id']
        try:
            vid.duration = child['duration']
        except:
            vid.duration = 0
        vids.append(vid)
    return vids

def attemptLogin(username, password, encoded=False):
    encpass = getEncodedPassword(password) if not encoded else password
    url = getSubsonicLoginUrl(username, encpass)
    xml = get_xml(url)
    soup = BeautifulSoup(xml)
    resp = soup.find('subsonic-response')
    success = False
    if resp:
        success = resp['status'] == "ok"
    return success
    
def getNowPlaying(sonic_user, sonic_pass):
    url = getSubsonicUrl("getNowPlaying", sonic_user, sonic_pass)
    xml = get_xml(url)
    soup = BeautifulSoup(xml)
    entries = soup.findAll("entry", isvideo="true")
    all = []
    for item in entries:
        entry = NowPlayingEntry()
        entry.id = item['id']
        entry.title = item['title']
        #entry.album = item['album']
        #entry.artist = item['artist']
        entry.duration = int(item['duration'])
        #entry.bitrate = int(item['bitrate'])
        entry.size = int(item['size'])
        entry.path = item['path']
        entry.username = item['username']
        entry.playerid = int(item['playerid'])
        entry.playername = item['playername']
        entry.minutesago = int(item['minutesago'])
        all.append(entry)
    return all
    
    
def getSubsonicVideoUrl(id, bitrate=1000, offset=0):
    return "http://{0}:{1}/videoPlayer.view?id={2}&maxBitRate={3}&timeOffset={4}&popout=true".format(settings.SUBSONIC.internal_host, settings.SUBSONIC.port, id, bitrate, offset)

def getHLSUrl(id, bitrate=500, offset=0, sonic_user="", sonic_pass=""):
    return "http://{0}:{1}/rest/hls.m3u8?id={2}&bitRate={3}&timeOffset={4}&u={5}&p={6}&v=1.8.0&c=brdflix".format(settings.SUBSONIC.internal_host, settings.SUBSONIC.port, id, bitrate, offset, sonic_user, sonic_pass)
    
def getHLSAutoBitrateUrl(id, offset=0, sonic_user="", sonic_pass=""):
    return "http://{0}:{1}/rest/hls.m3u8?id={2}&bitRate=320&bitRate=500&bitRate=1000&bitRate=1500&bitRate=2000&timeOffset={3}&u={4}&p={5}&v=1.8.0&c=brdflix".format(settings.SUBSONIC.internal_host, settings.SUBSONIC.port, id, offset, sonic_user, sonic_pass)

def getEncodedPassword(password):
    return "enc:{0}".format(password.encode("hex"))
    
def main():
    pass
    
if __name__ == "__main__":
    exit(main())
