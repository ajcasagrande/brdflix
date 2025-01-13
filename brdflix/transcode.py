import time
import subprocess
import uuid
import os
import re
import shlex
import shutil
import json
import base64
import hashlib
import sys
import locale
from datetime import datetime
from pprint import pprint
from threading import Thread

import brdflix
import xbmc
from db_mysql import DEFAULT as db
from datatypes import *
import settings
from helpers import *

FFMPEG_EXE = os.path.join(brdflix.TRANSCODE_DIR, 'ffmpeg64.exe')
FFMPEG_HLS_EXE = os.path.join(brdflix.TRANSCODE_DIR, 'ffmpeg64_hls.exe')
FFPROBE_EXE = os.path.join(brdflix.TRANSCODE_DIR, 'ffprobe64.exe')
FFMS_EXE = os.path.join(brdflix.TRANSCODE_DIR, 'ffms', 'ffmsindex.exe')

os.environ['FC_CONFIG_FILE'] = 'fonts.conf'
os.environ['FC_CONFIG_DIR'] = brdflix.TRANSCODE_DIR
os.environ['FC_CONFIG_PATH'] = brdflix.TRANSCODE_DIR

M3U8_PROCESSES = {}

ACTIVE_PROCESSES = []

class FfmpegInfo:
    def __init__(self):
        self.duration = 0.0
        self.bitrate = 0
        self.audio = []
        self.video_index = 0
        self.video_width = 0
        self.video_height = 0 
        self.video_codec = ""
        self.eng_stream = None
        self.fps = ""
        self.format_name = ""

class TranscodeProcess:
    def __init__(self):
        self.process = None
        self.cmds = ""
        self.last_active = time.time()
        self.start_time = None
        self.guid = uuid.uuid4()
        
        self.fname = ""
        self.offset = 0
        self.offset2 = 0
        self.duration = 0
        self.volume = 1024
        self.bitrate = 500
        self.width = 854
        self.height = 480
        self.video_stream = 0
        self.audio_stream = 1
        self.srt_stream = 2
        self.show_srt = False
        self.srt_fname = ""
        self.frequency = 1
        self.cwd = None
        self.outfile = None
        self.media_id = None
        self.crop_3d_sbs = False
        self.threads = 2
        self.channels = 2
        self.media = None
        
        self.m3u8_cwd = None
        self.m3u8_sha1 = None
        self.m3u8_details = None
        self.username = None

        self.transfer_size = 0L
        self.stream_obj = None
        
    def setup_jinja(self, fn):
        t, j = get_jinja_template(u"transcode/{0}.ff".format(fn))

        j.ffmpeg = FFMPEG_EXE
        j.ffmpeg_hls = FFMPEG_HLS_EXE
        j.ffprobe = FFPROBE_EXE
        j.ffms = FFMS_EXE
        j.fname = self.fname
        j.offset = self.offset
        j.offset2 = self.offset2
        j.duration = self.duration
        j.volume = self.volume
        j.bitrate = self.bitrate
        j.width = self.width
        j.height = self.height
        j.crop_3d_sbs = self.crop_3d_sbs
        j.frequency = self.frequency
        j.outfile = self.outfile
        j.threads = self.threads
        j.channels = self.channels
        j.media = self.media
        j.mappings = "-map 0:{0} -map 0:{1}".format(self.video_stream, self.audio_stream)
        j.srt = "" if (not self.show_srt or self.srt_fname == "") else ('-vf "ass=' + self.srt_fname + '"')
        j.srt_stream = self.srt_stream

        self.cmd = re.sub(u' +', ' ', t.render(j.kwargs()).replace('\n', ' '))
        
        self.cmds = shlex.split(self.cmd.encode('utf-8'))
        for i in range(len(self.cmds)):
            self.cmds[i] = self.cmds[i].decode('utf-8').encode(locale.getpreferredencoding())

    def setup(self, fn):
        cmdFile = unicode(os.path.join(brdflix.TRANSCODE_DIR, fn + '.txt'))
        with open(cmdFile, u'r') as f:
            cmd = f.read()
        f.close()

        args = {}
        args['[ffmpeg]'] = FFMPEG_EXE
        args['[ffmpeg_hls]'] = FFMPEG_HLS_EXE
        args['[ffprobe]'] = FFPROBE_EXE
        args['[ffms]'] = FFMS_EXE
        args['[fname]'] = self.fname
        args['[offset]'] = self.offset
        args['[offset2]'] = self.offset2
        args['[duration]'] = self.duration
        args['[volume]'] = self.volume
        args['[bitrate]'] = self.bitrate
        args['[width]'] = self.width
        args['[height]'] = self.height
        args['[frequency]'] = self.frequency
        args['[outfile]'] = self.outfile
        args['[mappings]'] = "-map 0:{0} -map 0:{1}".format(self.video_stream, self.audio_stream)
        args['[srt]'] = "" if (not self.show_srt or self.srt_fname == "") else ('-vf "ass=' + self.srt_fname + '"')
        args['[srt_stream]'] = self.srt_stream
        for key in args.keys():
            cmd = cmd.replace(key, unicode(args[key]))
        self.cmd = re.sub(ur"  +", u" ", cmd)

        self.cmds = shlex.split(self.cmd.encode('utf-8'))
        for i in range(len(self.cmds)):
            self.cmds[i] = self.cmds[i].decode('utf-8').encode(locale.getpreferredencoding())
    
    def run_m3u8(self, username, cwd, sha1, details):
        self.m3u8_cwd = cwd
        self.m3u8_sha1 = sha1
        self.m3u8_details = details
        self.username = username
        if not username in M3U8_PROCESSES.keys():
            M3U8_PROCESSES[username] = []
        
        #cleanup any currently running processes for this user
        to_remove = []        
        for m in M3U8_PROCESSES[username]:
            if m.process.poll() is None:
                m.process.kill()
                print "KILLED M3U8 PROCESS:", m.guid, m.m3u8_details
                # time.sleep(0.2)                
                # try: 
                    # shutil.rmtree(m.m3u8_cwd)
                # except:
                    # print "Unable to remove dir:", m.m3u8_cwd
                to_remove.append(m)
        for t in to_remove:
            M3U8_PROCESSES[username].remove(t)
                
            
        M3U8_PROCESSES[username].append(self)
        with open(os.devnull, 'w') as devnull:
            print "Starting m3u8 process:", self.guid, self.m3u8_details  
            self.process = subprocess.Popen(self.cmds, cwd=cwd, stdout=devnull, stderr=devnull)
    
    def run(self, print_cmd=False):
        self.last_active = time.time()
        self.start_time = time.time()
        if print_cmd:
            print self.cmd
        if self.cwd is None:
            self.process = subprocess.Popen(self.cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            self.process = subprocess.Popen(self.cmds, cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ACTIVE_PROCESSES.append(self)
    
    def run_monitored(self, interval=1, timeout=5):
        self.run()
        thread = Thread(target=transcode_watcher, args=[self, interval, timeout])
        thread.daemon = True
        thread.start()

    def result(self, max_mbps=10.0, boost_seconds=10.0, boost_mbps=None):
        yield_lines = 100
        poll_interval = 100 # poll_interval should be a multiple of yield_lines
        insert_interval_ms = 1000

        convert_mbps_bypms = 131.072
        max_bypms = max_mbps * convert_mbps_bypms
        boost_bypms = None if boost_mbps is None else boost_mbps * convert_mbps_bypms
        boost_ms = boost_seconds * 1000
        min_sleep_ms = 20 # The least amount of time to sleep, if less than this, don't sleep

        part = StreamPart()
        part.stream_id = self.stream_obj.id
        part.start_ms = int(round(time.time() * 1000))
        part.start_bytes = 0L

        self.active_part = part
        self.transfer_size = 0L
        self.start_ms = int(round(time.time() * 1000))
        last_ms = self.start_ms
        last_size = 0L
        line = self.process.stdout.readline()
        lines = []
        i = 1
        while line:
            lines.append(line)
            self.transfer_size += sys.getsizeof(line)

            if i % yield_lines == 0:
                yield ''.join(lines)
#                diff_size = self.transfer_size - last_size
#                last_size = self.transfer_size
#                diff_ms = int(round(time.time() * 1000)) - last_ms
#                last_ms = int(round(time.time() * 1000))
#                print "yielded {0} kb in {1} ms".format(diff_size / 1024.0, diff_ms)
                lines = []

            if i % poll_interval == 0:
                diff_size = self.transfer_size - part.start_bytes
                diff_ms = int(round(time.time() * 1000)) - part.start_ms
                if int(round(time.time() * 1000)) - self.start_ms > boost_ms:
                    x = (diff_size - (max_bypms * diff_ms)) / max_bypms
                    #print "x: {0}, orig: {1}, new: {2}".format(x, diff_size / diff_ms / convert_mbps_bypms, diff_size / (diff_ms + x) / convert_mbps_bypms)
                    if x >= min_sleep_ms:
                        time.sleep(x / 1000.0)
                elif boost_bypms is not None:
                    x = (diff_size - (boost_bypms * diff_ms)) / boost_bypms
                    #print "x: {0}, orig: {1}, new: {2}".format(x, diff_size / diff_ms / convert_mbps_bypms, diff_size / (diff_ms + x) / convert_mbps_bypms)
                    if x >= min_sleep_ms:
                        time.sleep(x / 1000.0)
                if int(round(time.time() * 1000)) - part.start_ms >= insert_interval_ms:
                    part.end_bytes = self.transfer_size
                    part.end_ms = int(round(time.time() * 1000))
                    part.insert()

                    # reset part object
                    part = StreamPart()
                    part.stream_id = self.stream_obj.id
                    part.start_ms = int(round(time.time() * 1000))
                    part.start_bytes = self.transfer_size
                    self.active_part = part

            line = self.process.stdout.readline()
            i += 1
        print "Ffmpeg finsihed transcoding!"
        if self.stream_obj and self.stream_obj.id:
            self.stream_obj.end_time = datetime.now()
            self.stream_obj.transfer_size = self.transfer_size
            self.stream_obj.update(['start_time', 'end_time', 'transfer_size'])
        if self.active_part and not self.active_part.id:
            self.active_part.end_ms = int(round(time.time() * 1000))
            self.active_part.end_bytes = self.transfer_size
            self.active_part.insert()
        # remove from list of active because done transferring
        if self.process in ACTIVE_PROCESSES:
            ACTIVE_PROCESSES.remove(self.process)
        # delete the process to clean up handles
        del self.process

    def result_good(self):
        self.transfer_size = 0L
        line = self.process.stdout.readline()
        while line:
            yield line
            self.transfer_size += sys.getsizeof(line)
            line = self.process.stdout.readline()

    def result_old(self):
        interval = 250
        i = 1
        self.last_active = time.time()
        line = self.process.stdout.readline()
        while line:
            yield line
            line = self.process.stdout.readline()
            i = i + 1
            if i == interval:
                i = 0
                self.last_active = time.time()
        print "Exited result loop"

def transcode_watcher(p, interval=1, timeout=5):
    killed = False
    while p.process.poll() is None:
        time.sleep(interval)
        #print p.guid, ':', time.time() - p.last_active
        if time.time() - p.last_active > timeout:
            killed = True
            print "KILLING orphaned ffmpeg64 :", p.guid
            p.process.kill()
            break
    if not killed:
        print 'Finished ffmpeg64 :', p.guid, 'in', int(round(time.time() - p.start_time)), 'seconds'
    if p in ACTIVE_PROCESSES:
        ACTIVE_PROCESSES.remove(p)
    return killed

class Frame:
    def __init__(self):
        self.number = 0
        self.timestamp = ""
        self.fps = 0.0
        self.duration = 0.0
    
def getM3U8File(fname):
    sha1 = hashlib.sha1(fname).hexdigest()
    m3u8_file = os.path.join(settings.GLOBAL.temp_dir, sha1 + ".m3u8")
    if os.path.isfile(m3u8_file):
        return m3u8_file
    
    info = getVideoInfo(fname)
    path64 = base64.b64encode(fname)
    start = time.time()
    p = TranscodeProcess()
    p.fname = fname
    p.setup('frames')
    p.run()
    resStr = p.process.communicate()[0]
    res = json.loads(resStr)
    frames = []
    for f in res['frames']:
        if 'pict_type' in f and f['pict_type'] == 'I':
            frame = Frame()
            frame.number = int(f['coded_picture_number'])
            frame.timestamp = f['pkt_pts_time']
            frame.fps = 0.0 if float(frame.timestamp) == 0.0 else frame.number / float(frame.timestamp)
            frames.append(frame)
    end = time.time()
    print "Finished in:", end - start
     
    segments = []
    segments.append(frames[0])
    segment_length = 10
    num = segment_length
    #dont count start frame
    for i in range(len(frames) - 2):
        f1 = frames[i+1]
        f2 = frames[i+2]
        if float(f2.timestamp) > num:
            d1 = abs(num - float(f1.timestamp))
            d2 = abs(float(f2.timestamp) - num)
            if d1 < d2:
                segments.append(f1)
            else:
                segments.append(f2)
            num = num + segment_length
    for i in range(len(segments) - 1):
        s0 = segments[i]
        s1 = segments[i+1]
        s0.duration = float(s1.timestamp) - float(s0.timestamp)
    segments[len(segments) - 1].duration = info.duration - float(segments[len(segments) - 1].timestamp)
    
    with open(m3u8_file, "w") as f:
        f.write(u"#EXTM3U\n")
        f.write(u"#EXT-X-VERSION:3\n")
        f.write(u"#EXT-X-MEDIA-SEQUENCE:0\n")
        f.write(u"#EXT-X-TARGETDURATION:{0}\n".format(segment_length))
        for s in segments:
            #print s.number,'|', s.timestamp, '|', s.duration
            f.write(u"#EXTINF:{0},\n".format(s.duration))
            f.write(u"/hls/segment.ts?offset={0}&duration={1}&path64={2}\n".format(s.timestamp.rstrip('0').rstrip('.'), s.duration, path64))
        f.write(u"#EXT-X-ENDLIST\n")
    print len(segments), "total segments."
    # delete the process to clean up handles
    del p.process
    return m3u8_file
    
def getVideoInfo(fname):
    if not os.path.isfile(fname):
        return None
    info = FfmpegInfo()
    p = TranscodeProcess()
    p.fname = fname
    p.setup('info')
    p.run()
    resStr = p.process.communicate()[0]
    #print resStr
    res = json.loads(resStr)
    info.duration = float(res['format']['duration'])
    info.bitrate = int(res['format']['bit_rate'])
    info.size = int(res['format']['size'])
    info.format_name = res['format']['format_name']
    
    info.audio = []
    info.subs = []
    info.audios = []
    for s in res['streams']:
        if s['codec_type'] == 'video':
            info.video_index = int(s['index'])
            info.video_width = int(s['width'])
            info.video_height = int(s['height']) 
            info.video_codec = s['codec_name']
            info.fps = s['avg_frame_rate']
            if info.fps == '0/0':
                info.fps = s['r_frame_rate']
        elif s['codec_type'] == 'audio':
            au = xbmc.AudioStream()
            au.index = int(s['index'])
            au.codec = s['codec_name']
            if 'tags' in s and 'language' in s['tags']:
                au.lang = s['tags']['language']
            else:
                au.lang = "unknown"
            au.channels = int(s['channels'])
            info.audio.append(au)


            a = MediaAudio()
            a.stream_index = int(s['index'])
            a.codec = s['codec_name']
            a.codec_long = s['codec_long_name']
            if 'tags' in s and 'language' in s['tags']:
                a.language = s['tags']['language']
            else:
                a.language = "unknown"
            if 'tags' in s and 'title' in s['tags']:
                a.title = s['tags']['title']
            else:
                a.title = ""
            if 'disposition' in s:
                a.comment = int(s['disposition']['comment'])
                a.forced = int(s['disposition']['forced'])
                a.default = int(s['disposition']['default'])
            a.channels = int(s['channels'])
            a.sample_fmt = s['sample_fmt']
            a.bit_rate = int(s['bit_rate']) if 'bit_rate' in s else None
            a.sample_rate = int(s['sample_rate']) if 'sample_rate' in s else None
            info.audios.append(a)
        elif s['codec_type'] == 'subtitle':
            sub = MediaSubtitle()
            sub.stream_index = int(s['index'])
            sub.codec = s['codec_name']
            sub.codec_long = s['codec_long_name']
            if 'tags' in s and 'language' in s['tags']:
                sub.language = s['tags']['language']
            else:
                sub.language = "unknown"
            if 'tags' in s and 'title' in s['tags']:
                sub.title = s['tags']['title']
            else:
                sub.title = ""
            if 'disposition' in s:
                sub.comment = int(s['disposition']['comment'])
                sub.forced = int(s['disposition']['forced'])
                sub.default = int(s['disposition']['default'])
            info.subs.append(sub)

    max_channels = 0
    for au in info.audio:
        if au.channels > max_channels:
            max_channels = au.channels
            if au.lang == "unknown":
                info.eng_stream = au
        if au.lang == "eng" and au.channels >= max_channels:
            info.eng_stream = au
            break

    # delete the process to clean up handles
    del p.process
    #print "FPS:", info.fps
    #pprint(info.__dict__)
    return info
            