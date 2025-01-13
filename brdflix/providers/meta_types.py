import base64

class BaseEpisode(object):
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
        self.watched = False
        self.resume = ""
        self.thumb_path = None
        self.firstaired = ""

    @property
    def thumbpath64(self):
        return "" if self.thumb_path is None else base64.b64encode(self.thumb_path)

    def __repr__(self):
        return "{0} - {1}x{2} - {3}".format(self.showName, self.season, str(self.episode).zfill(2), self.epName)

class BaseSeason(object):
    def __init__(self):
        pass        
        
class BaseShow(object):
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
        
class BaseMovie(object):
    def __init__(self):
        pass
        