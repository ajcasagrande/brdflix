
from base_providers import *
import brdflix.xbmc as xbmc

class XBMCProvider(TVProvider, MovieProvider, FileProvider):
    def __init__(self):
        pass

    def get_episodes(self, id_show, season=-1):
        return xbmc.getEpisodes(id_show, season)
       
    def get_episode_info(self, id_episode):
        return xbmc.getEpisodeInfo(id_episode)
        
    def get_recent_episodes(self):
        return xbmc.getRecentEpisodes()
        
    def get_seasons(self, id_show):
        return xbmc.getSeasons(id_show)
        
    def get_shows(self):
        return xbmc.getShows()
        
    def get_show_info(self, id_show):
        return xbmc.getShowInfo(id_show)
        
    def get_show_poster(self, id_show):
        return xbmc.getShowPoster()
        
    def get_show_tvdb_id(self, id_show):
        return xbmc.getShowTVDB_ID(id_show)