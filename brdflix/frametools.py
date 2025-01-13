import sys
import base64
from threading import Thread

import brdflix
import xbmc
from transcode import *
from datatypes import *
from db_mysql import DEFAULT as db
import settings

def generate_media_index(media, wait=False):
    p = TranscodeProcess()
    path = os.path.join(settings.GLOBAL.temp_dir, 'ffindex')
    if not os.path.exists(path):
        os.makedirs(path)
    p.fname = xbmc.getLocalPathFromPath64(media.path64)
    p.outfile = os.path.join(path, 'media_' + str(media.id) + '.ffindex')
    p.setup('ffms/key_frames')
    p.run()

    if wait:
        media_generate_thread(media, p)
    else:
        thread = Thread(target=media_generate_thread, args=[media, p])
        thread.daemon = True
        thread.start()

def media_generate_thread(media, p):
    p.process.communicate()
    # delete the process to clean up handles
    del p.process
    outname = "{0}_track{1:02}.kf.txt".format(p.outfile, media.video_stream)
    #print outname
    frames = create_key_timecodes(outname, media.fps)
    if frames is not None:
        # Insert frames into media_frame table in db
        for fn, tc in frames:
            frame = MediaFrame()
            frame.media_id = media.id
            frame.num = fn
            frame.time = tc
            db.insert_generic(frame)

def generate_index(play_id, path64, wait=False):
    p = TranscodeProcess()
    path = os.path.join(settings.GLOBAL.temp_dir, 'ffindex')
    if not os.path.exists(path):
        os.makedirs(path)
    p.fname = xbmc.getLocalPathFromPath64(path64)
    p.outfile = os.path.join(path, str(play_id) + '.ffindex')
    p.setup('ffms/key_frames')
    p.run()
    if wait:
        p.process.communicate()
        # delete the process to clean up handles
        del p.process
        return os.path.join(path, str(play_id) + '.ffindex_track00.kf.txt')

def create_key_timecodes(infile, fps):
    frames = []
    if '/' in str(fps):
        tokens = fps.split('/')
        fps_top = float(tokens[0])
        fps_bottom = float(tokens[1])
        if fps_bottom == 0.0:
            print "ERROR! FPS_BOTTOM WAS 0! FPS:", fps
            return None
        #print fps_top, '/', fps_bottom
    else:
        tokens = None
        fps = float(fps)
    file = open(infile, 'r')
    line = file.readline()
    i = 1
    while line is not None and line != '':
        if i > 2 and line != '':
            if tokens is not None:
                values = (int(line), int(line) / (fps_top / fps_bottom))
            else:
                values = (int(line), int(line) / fps)
            frames.append(values)
        line = file.readline()
        i += 1
    return frames

# return (offset, duration)
def get_segments(frames, segment_dur):
    res = []
    last_offset = 0.0
    for i in range(len(frames)-2):
        fn1, tc1 = frames[i]
        fn2, tc2 = frames[i+1]
        dur2 = round(tc2 - last_offset, 3)
        if dur2 >= segment_dur:
            dur1 = round(tc1 - last_offset, 3)
            if abs(dur1 - segment_dur) < abs(dur2 - segment_dur):
                res.append((last_offset, dur1))
                last_offset += dur1
            else:
                res.append((last_offset, dur2))
                last_offset += dur2
    #add last part
    fn, tc = frames[len(frames)-1]
    res.append((last_offset, round(tc - last_offset, 3)))
    return res


def get_closest_media_frame(media_id, seconds, allow_over=True):
    media = Media().from_id(int(media_id))
    if media is None or media.frames is None or len(media.frames) == 0:
        return None
    for i in range(len(media.frames)):
        f1 = media.frames[i]
        if f1.time > seconds:
            f2 = media.frames[i-1]
            if allow_over and i > 0:
                # Check to see which frame is actually closer to target seconds
                if abs(seconds - f2.time) < abs(f1.time - seconds):
                    return f2
                else:
                    return f1
            else:
                return f2 if i > 0 else f1
    return None

def get_closest_frame(infile, seconds, fps, allow_over=True):
    frames = create_key_timecodes(infile, fps)
    for i in range(len(frames)):
        fn, tc = frames[i]
        if tc > seconds:
            if allow_over and i > 0:
                # Check to see which frame is actually closer to target seconds
                fn1, tc1 = frames[i-1]
                if abs(seconds - tc1) < abs(tc - seconds):
                    return frames[i-1]
                else:
                    return frames[i]
            else:
                return frames[i-1] if i > 0 else frames[0]
