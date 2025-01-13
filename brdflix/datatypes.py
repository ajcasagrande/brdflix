import time
from datetime import datetime, timedelta
from pprint import pprint, pformat
import base64

import brdflix
from db_mysql import DEFAULT as db

class DatabaseObject(object):
    _table_name = None
    _id_column = "id"
    _ignore_list = [ _id_column ]

    def __init__(self, _strict_mode=False, **kwargs):
        """
        Pass in whatever instance variables you want set as kwargs.
        This can be called from any subclass in order to easily
        create instance objects. This should be called last
        as to prevent values being overridden with None.
        @strict_mode makes it so that only values that are
        already defined (usually set to None) can be set.
        --- this:
        obj = DatabaseObject()
        obj.id = 5
        obj.name = 'string'
        --- becomes:
        obj = DatabaseObject(id=5, name='string')
        """
        for key, val in kwargs.items():
            if not _strict_mode or key in self.__dict__:
                self.__dict__[key] = val

    def get_id(self):
        return self.__dict__[self._id_column]

    def set_id(self, val):
        self.__dict__[self._id_column] = val

    def dump(self):
        pprint(self.__dict__)

    def dump_str(self):
        return pformat(self.__dict__)

    def insert(self, replace_into=False):
        """
        Insert this item into the database, optionally "REPLACE INTO"
        """
        return db.insert_generic(self, replace_into=replace_into)

    def insert_or_update(self):
        return db.insert_or_update_generic(self)

    def update_full(self):
        return db.update_generic_full(self)

    def update(self, what_list=None):
        return db.update_generic(self, what_list)

    def delete(self):
        return db.delete_generic(self)

    def from_id(self, id, include_extras=False):
        kwargs = { self._id_column : id }
        return self.query_one(include_extras=include_extras, **kwargs)

    def query_all(self, limit=None, order_by=None, include_extras=False, _log=False, **kwargs):
        #TODO: Does kwargs.keys() and kwargs.values() return items in the same order?
        where_clause = limit_clause = order_clause = ''
        if kwargs is not None and len(kwargs.keys()) > 0:
            where_clause = ' where ' + ' and '.join([ '`{0}`=%s'.format(key) for key in kwargs.keys() ])
        if limit is not None:
            limit_clause = ' limit {0} '.format(limit)
        if order_by is not None:
            order_clause = ' order by {0} '.format(order_by) if not order_by.strip().startswith('order') else order_by
        query = 'select * from `{0}` {1} {2} {3} '.format(self._table_name, where_clause, order_clause, limit_clause)
        if _log:
            print query
            pprint(kwargs)
        rows = db.fetch_all(query, tuple(kwargs.values()))
        if _log:
            print 'Total rows returned:', len(rows)
        return self._create_objects(rows, include_extras)

    def query_one(self, order_by=None, include_extras=False, _log=False, **kwargs):
        all = self.query_all(limit=1, order_by=order_by, include_extras=include_extras, _log=_log, **kwargs)
        res = all[0] if all is not None else None
        if _log:
            res.dump()
        return res

    def raw_query_one(self, query, values, include_extras=False):
        row = db.fetch_one(query, values)
        return self._create_object(row, include_extras)

    def raw_query_all(self, query, values, include_extras=False):
        rows = db.fetch_all(query, values)
        return self._create_objects(rows, include_extras)

    def _create_objects(self, rows, include_extras=False):
        if rows is None or len(rows) == 0:
            return None
        else:
            return [ db.get_generic(self.__class__(), row, include_extras) for row in rows ]

    def _create_object(self, row, include_extras=False):
        return db.get_generic(self, row, include_extras)

class Request(DatabaseObject):
    _table_name = "request"

    def __init__(self, **kwargs):
        self.id = None
        self.port = brdflix.PORT
        self.method = ""
        self.ip_address = ""
        self.request = ""
        self.timestamp = datetime.now()
        self.user_id = None
        self.user_agent = ""
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

class BlockedRequest(DatabaseObject):
    _table_name = "blocked_request"

    def __init__(self, _req_obj=None, **kwargs):
        self.id = None
        self.port = brdflix.PORT
        self.method = ""
        self.ip_address = ""
        self.full_ip = ""
        self.request = ""
        self.base = ""
        self.http_code = -1
        self.known_host_id = -1
        self.timestamp = datetime.now()
        self.user_agent = ""
        self.referer = ""

        if _req_obj is not None:
            self.update_from_request(_req_obj)
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

    def update_from_request(self, req):
        self.method = req.method
        self.ip_address = req.ip_address
        self.request = req.request
        self.user_agent = req.user_agent

class User(DatabaseObject):
    _table_name = "user"

    def __init__(self, **kwargs):
        self.id = None
        self.enabled = False
        self.group_id = 0
        self.username = ""
        self.password = ""
        self.email = ""
        self.watched_status = False
        self.allow_email = True
        self.last_access = None
        self.last_ip = None

        self._group = None
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

    def from_name(self, username):
        res = self.query_one(username=username)
        return res

    def to_zl(self):
        return base64.b64encode(self.username + '$$' + self.password)

    @property
    def group(self):
        # Lazy load group
        if self._group is None:
            self._group = Group().from_id(self.group_id)
        return self._group

class Quality(DatabaseObject):
    _table_name = "quality"

    def __init__(self, **kwargs):
        self.id = None
        self.sort_index = 0
        self.name = ""
        self.bitrate = 0
        self.width = 0
        self.height = 0
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

class MediaFrame(DatabaseObject):
    _table_name = "media_frame"

    def __init__(self, **kwargs):
        self.id = None
        self.media_id = 0L
        self.num = 0L
        self.time = 0.0
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

class MediaSubtitle(DatabaseObject):
    _table_name = "media_sub"

    def __init__(self, **kwargs):
        self.id = None
        self.media_id = -1
        self.language = ""
        self.title = ""
        self.codec = ""
        self.codec_long = ""
        self.stream_index = -1
        self.comment = 0
        self.forced = 0
        self.default = 0
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

class MediaAudio(DatabaseObject):
    _table_name = "media_audio"

    def __init__(self, **kwargs):
        self.id = None
        self.media_id = -1
        self.channels = -1
        self.sample_fmt = ""
        self.language = ""
        self.title = ""
        self.codec = ""
        self.codec_long = ""
        self.stream_index = -1
        self.comment = 0
        self.forced = 0
        self.default = 0
        self.sample_rate = -1
        self.bit_rate = -1
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

class Media(DatabaseObject):
    _table_name = "media"

    def __init__(self, _info_obj=None, _hash_obj=None, **kwargs):
        self.id = None
        self.sha1 = ""
        self.path64 = ""
        self.fname = ""
        self.bytes = 0L
        self.mod_time = 0.0
        self.movie_id = None
        self.show_id = None
        self.episode_id = None
        self.is_trailer = False
        self.fps = ""
        self.duration = 0.0
        self.width = 0
        self.height = 0
        self.bitrate = 0
        self.video_stream = 0
        self.audio_stream = 1
        self.video_codec = ""
        self.audio_codec = ""
        self.audio_channels = 0
        self.format_name = ""
        self.rescan = False

        if _info_obj is not None:
            self.update_video_info(_info_obj)
        if _hash_obj is not None:
            self.update_hash(_hash_obj)

        self._frames = None
        self._audio_tracks = None
        self._subtitles = None
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

    @property
    def frames(self):
        # Lazy load media_frame
        if self._frames is None:
            self._frames = MediaFrame().query_all(media_id=self.id)
        return self._frames

    @property
    def audio_tracks(self):
        # Lazy load media_audio
        if self._audio_tracks is None:
            self._audio_tracks = MediaAudio().query_all(media_id=self.id)
        return self._audio_tracks

    @property
    def subtitles(self):
        # Lazy load media_sub
        if self._subtitles is None:
            self._subtitles = MediaSubtitle().query_all(media_id=self.id)
        return self._subtitles

    def update_hash(self, hash):
        """
        Update this object with data from a Hash object
        """
        self.sha1 = hash.value
        self.bytes = hash.filesize
        self.mod_time = hash.mod_time

    def update_video_info(self, info):
        """
        Update this object with data from an FfmpegInfo object
        """
        self.duration = info.duration
        self.fps = info.fps
        self.bitrate = info.bitrate
        self.width = info.video_width
        self.height = info.video_height
        self.format_name = info.format_name

        self.video_stream = info.video_index
        self.video_codec = info.video_codec

        au = info.eng_stream if info.eng_stream is not None else info.audio[0]
        self.audio_stream = au.index
        self.audio_codec = au.codec
        self.audio_channels = au.channels

    def from_sha1(self, sha1):
        return self.query_one(sha1=sha1)

class Resume(DatabaseObject):
    _table_name = "resume"

    def __init__(self, **kwargs):
        self.id = None
        self.user_id = 0
        self.media_id = None
        self.offset = 0.0
        self.auto = True
        self.timestamp = None
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

    def getPrettyOffset(self):
        td = timedelta(seconds=self.offset)
        val = str(td)
        if val.startswith('0:'):
            val = val[2:]
        if '.' in val:
            val = val[:val.rfind('.')]
        return val

    def getSaveType(self):
        if self.auto:
            return "auto-saved"
        else:
            return "user-saved"

class ImageCache(DatabaseObject):
    _table_name = "image_cache"
    _ignore_list = [ ]

    def __init__(self, **kwargs):
        self.id = ""
        self.path64 = None
        self.fname = ""
        self.w = None
        self.h = None
        self.type = None
        self.last_updated = None
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

class StreamPart(DatabaseObject):
    _table_name = "stream_part"

    def __init__(self, **kwargs):
        self.id = None
        self.stream_id = 0
        self.start_ms = 0L
        self.end_ms = 0L
        self.start_bytes = 0L
        self.end_bytes = 0L
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

class Stream(DatabaseObject):
    _table_name = "stream"

    def __init__(self, **kwargs):
        self.id = None
        self.user_id = None
        self.play_id = None
        self.download_id = None
        self.media_id = None
        self.request_id = None
        self.quality_id = None
        self.format = ""
        self.offset = 0
        self.volume = 0
        self.start_time = datetime.now()
        self.end_time = None
        self.transfer_size = None
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

    def update_process(self, p):
        self.offset = p.offset
        self.volume = p.volume

class FavoriteShow(DatabaseObject):
    _table_name = "favorite_show"

    def __init__(self, **kwargs):
        self.id = None
        self.user_id = None
        self.xbmc_id = None
        self.tvdb_id = None
        self.notify = True
        self.show_name = ""
        self.added = datetime.now()
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

    @staticmethod
    def get_all_from_user(user_id):
        rows = db.fetch_all("SELECT * FROM `favorite_show` WHERE `user_id`=%s ORDER BY `show_name`", (user_id,))
        return [ db.get_generic(FavoriteShow(), row, False) for row in rows ]

class EmailNotification(DatabaseObject):
    _table_name = "email_notification"

    def __init__(self, **kwargs):
        self.id = None
        self.user_id = None
        self.episode_id = None
        self.timestamp = datetime.now()
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

    @staticmethod
    def get_all_from_user(user_id):
        rows = db.fetch_all("SELECT * FROM `email_notification` WHERE `user_id`=%s ORDER BY `timestamp`", (user_id,))
        return [ db.get_generic(EmailNotification(), row, False) for row in rows ]

class WatchlistItem(DatabaseObject):
    _table_name = "watchlist_item"

    def __init__(self, **kwargs):
        self.id = None
        self.user_id = None
        self.xbmc_id = None
        self.movie_name = ""
        self.added = datetime.now()
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

    @staticmethod
    def get_all_from_user(user_id):
        rows = db.fetch_all("SELECT * FROM `watchlist_item` WHERE `user_id`=%s ORDER BY `movie_name`", (user_id,))
        return [ db.get_generic(WatchlistItem(), row, False) for row in rows ]

class Play(DatabaseObject):
    _table_name = "play"

    def __init__(self, **kwargs):
        self.id = None
        self.user_id = None
        self.media_id = None
        self.request_id = None
        self.start_time = datetime.now()
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

class Download(DatabaseObject):
    _table_name = "download"

    def __init__(self, **kwargs):
        self.id = None
        self.user_id = None
        self.media_id = None
        self.request_id = None
        self.raw = False
        self.start_time = datetime.now()
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

class Group(DatabaseObject):
    _table_name = "group"

    def __init__(self, **kwargs):
        self.id = None
        self.name = ""
        self.admin_rights = False
        self.xbmc_rights = False
        self.download_rights = False
        self.max_quality_id = 0
        self.default_quality_id = 0
        self.max_mobile_quality_id = 0
        self.default_mobile_quality_id = 0
        self.mbps_multiplier = 1
        self.download_multiplier = 1
        self.max_mbps = None
        self.boost_mbps = None
        self.boost_seconds = 0
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)
        
class KnownHost(DatabaseObject):
    _table_name = "known_host"

    def __init__(self, **kwargs):
        self.id = None
        self.ip_address = ""
        self.name = ""
        self.description = ""
        self.blocked = False
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

    def from_ip(self, ip):
        return self.query_one(ip_address=ip)


class XBMCServer(DatabaseObject):
    _table_name = "xbmc_server"

    def __init__(self, **kwargs):
        self.id = None
        self.name = ""
        self.host = ""
        self.external_host = None
        self.port = 0
        self.username = ""
        self.password = ""
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)

class PublicLink(DatabaseObject):
    _table_name = "public_link"

    def __init__(self, **kwargs):
        self.id = None
        self.created_by = -1
        self.media_id = -1
        self.quality_id = -1
        self.created = datetime.now()
        self.expires = None
        self.start_time = -1
        self.end_time = -1
        # Call this last to setup instance vars
        DatabaseObject.__init__(self, **kwargs)
