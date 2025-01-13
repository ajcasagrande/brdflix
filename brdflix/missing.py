import sickbeard

class MissingShow:
    def __init__(self):
        self.name = ""
        self.tvdb_id = 0
        self.xbmc_info = None
        self.sb_info = None
        self.total = 0
        self.seasons = []

class MissingSeason:
    def __init__(self):
        self.num = 0
        self.eps = []

class MissingEpisode:
    def __init__(self):
        self.season = 0
        self.episode = 0
        self.tvdb_id = 0
        self.epName = ""
        self.status = ""

def getMissing(show, season=-1):
    mshow = MissingShow()
    mshow.xbmc_info = show
    mshow.name = show.name
    mshow.tvdb_id = show.tvdb_id
    mshow.sb_info = sickbeard.getJSON("show.seasons", tvdbid=show.tvdb_id)['data']
    for key, val in mshow.sb_info.items():
        if str(key) != "0" and (int(season) == -1 or int(season) == int(key)):
            mseason = MissingSeason()
            mseason.num = int(key)
            for kep, vep in val.items():
                if vep['status'] in ['Skipped', 'Snatched', 'Wanted'] and vep['airdate'] != '':
                    if vep['status'] == 'Snatched':
                        # Check that the episode file does not exist first, drastically slower, but more accurate
                        info = sickbeard.getJSON('episode', tvdbid=show.tvdb_id, season=int(key), episode=int(kep))['data']
                        if info['location'].strip() != "":
                            # Has file info, so this is just a higher quality snatch, ignore this file
                            continue
                    ep = MissingEpisode()
                    ep.season = int(key)
                    ep.episode = int(kep)
                    ep.tvdb_id = show.tvdb_id
                    ep.epName = vep['name']
                    ep.status = vep['status']
                    mseason.eps.append(ep)
                    mshow.total += 1
            if len(mseason.eps) > 0:
                mshow.seasons.append(mseason)
    return mshow
