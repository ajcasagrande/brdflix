from threading import Thread

import frametools
from transcode import *
from datatypes import *
import hashes
import img
import settings
from threadpool import ThreadPool

def generate_thumbs(media, segments, width, height):
#    t = Thread(target=_gen_thumbs, args=[media, segments, width, height])
#    t.start()
    _gen_thumbs(media, segments, width, height)


def _gen_thumbs(media, segments, width, height):
    start = time.time()
    outpath = os.path.join(settings.GLOBAL.temp_dir, 'thumbs', str(media.id))
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    count = 0

    pool = ThreadPool(int(settings.GLOBAL.max_thumb_threads))
    for segment in segments:
        pool.add_task(_gen_thumb_thread, media, segment, outpath, width, height)
        count += 1
    pool.wait_completion()

    if count > 0:
        print "Generated", count, "thumbs in", time.time() - start, "seconds"

def _gen_thumb_thread(media, segment, outpath, width, height):
    outname = os.path.join(outpath, "{0}.jpg".format(segment.mid_time))
    if not os.path.isfile(outname):
        img.generate_thumb(media.path64, offset=segment.mid_time, width=width, height=height, outname=outname)

def get_or_create_media(path64, movieid, episodeid, showid, is_trailer):
    local_path = xbmc.getLocalPathFromPath64(path64)
    fname = local_path[local_path.rfind(u'/')+1:]
    hash = hashes.quick(local_path)
    media = Media().from_sha1(hash.value)
    if media is None or media.rescan:
        rescan = media is not None and media.rescan
        old_id = media.id if media is not None else None
        # Use ffprobe to ensure correct duration
        info = getVideoInfo(local_path)

        media = Media(_info_obj=info, _hash_obj=hash, path64=path64, fname=fname, is_trailer=is_trailer)
        media.show_id = int(showid) if showid else None
        media.episode_id = int(episodeid) if episodeid else None
        media.movie_id = int(movieid) if movieid else None
        if rescan:
            media.id = old_id
            media.rescan = False
            media.update_full()
            print "Media updated"
        else:
            media.insert()

        print "Media ID:", media.id
        for sub in info.subs:
            sub.media_id = media.id
            sub.insert()
        for audio in info.audios:
            audio.media_id = media.id
            audio.insert()
        if not rescan:
            frametools.generate_media_index(media)
    return media
