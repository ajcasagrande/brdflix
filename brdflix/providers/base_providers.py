
class MetadataProvider(object):
    def __init__(self):
        pass

class TVProvider(MetadataProvider):
    def __init__(self):
        pass

    def get_episodes(self, id_show, season=-1):
        """
        Return all episodes for a given show and a given season.
        If season equals -1, return episodes for every season.
        """
        return None

    def get_episode_info(self, id_episode):
        """
        Return the info for an episode with a given id.
        """
        return None

    def get_recent_episodes(self, id_show):
        """
        Get all recent episodes.
        """
        return None

    def get_seasons(self, id_show):
        """
        Get all seasons for a given show id.
        """
        return None

    def get_shows(self):
        """
        Get all tv shows.
        """
        return None

    def get_show_info(self, id_show):
        """
        Get the info for a tv show with the given id.
        """
        return None

    def get_show_poster(self, id_show):
        """
        Get the poster for a tv show with the given id.
        """
        return None

    def get_show_tvdb_id(self, id_show):
        """
        Get the tvdb  for a tv show with the given id.
        """
        return None


class MovieProvider(MetadataProvider):
    def __init__(self):
        pass

class FileProvider(MetadataProvider):
    def __init__(self):
        pass
