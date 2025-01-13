from datetime import datetime, timedelta

import brdflix
import sickbeard

def create_query(show, season, episode):
    return "{0}%20s{1:02}e{2:02}".format((show[:show.find(' (')] if ' (' in show else show).replace(" ", "%20").replace("&", ""), int(season), int(episode))
brdflix.jinja_env.filters['create_query'] = create_query

def sb_show_details_url(tvdb_id):
    return sickbeard.getShowDetailsUrl(tvdb_id)
brdflix.jinja_env.filters['sb_show_details_url'] = sb_show_details_url

def sort_seasons(seasons):
    return sorted(seasons, key=lambda s: s.num)
brdflix.jinja_env.filters['sort_seasons'] = sort_seasons

def sort_season_eps(eps):
    return sorted(eps, key=lambda e: e.episode)
brdflix.jinja_env.filters['sort_season_eps'] = sort_season_eps

def sb_status_css(status):
    return sickbeard.statusToCSS(status)
brdflix.jinja_env.filters['sb_status_css'] = sb_status_css

def sb_quality_css(quality):
    return sickbeard.qualityToCSS(quality)
brdflix.jinja_env.filters['sb_quality_css'] = sb_quality_css

def sb_coming_css(type):
    return sickbeard.comingTypeToCSS(type)
brdflix.jinja_env.filters['sb_coming_css'] = sb_coming_css


def pretty_days_away(days):
    if days is None:
        return "TDB"
    elif days == -1:
        return "Yesterday"
    elif days == 0:
        return "Today"
    elif days == 1:
        return "Tomorrow"
    elif days < -1:
        return "{0} Days Ago".format(days * -1)
    return "{0} Days".format(days)
brdflix.jinja_env.filters['pretty_days_away'] = pretty_days_away

def vtt_time(seconds):
    return "{0}{1:02}:{2:02}.{3:03}".format("" if seconds < (60*60) else "{0:02}:".format(int(seconds) / 60 / 60), (int(seconds) / 60) % 60, int(seconds) % 60, int(abs((int(seconds)-seconds)*1000)))
brdflix.jinja_env.filters['vtt_time'] = vtt_time
