BRDFlix
=========
Watch your XBMC videos transcoded on the fly using any flash based web browser.

This was created in ~2012-2013 around the timeframe when Netflix streaming was first starting to become mainstream (~2010-2011).
This is essentially what Plex.tv eventually became, but at the time, Plex hadn't even released a 1.0 yet, and this was quite fully featured comparatively.
I no longer recommend the use of this software, as apps such as Plex are much more suited today, however I have provided it to share the ideas, concepts, and code within.

Originally based on the `Subsonic` project, which I integrated with XBMC and called `XBMCSonic`, however through countless additions and modifications, it no longer resembles much of the original codebase, and was also renamed to `BRDFlix`.

> **Notice**  
> This project originally contained hard-coded sensitive data, and those values have been replaced with `<TODO>` inside the codebase.
> I don't really recommend anyone trying to use this. I have mostly provided it to share the ideas, concepts, and code within.

> Date:   Fri Jan 11 2013  
> _Initial Commit_  
> _Added all code from XBMCSonic project_
 

Features:
---------
- Multi user support w/ group based permissions, user favorites
- Specify max transfer speed (Mbps)
- Auto transcoding of video files for playback in the browser
- Ability to convert 3D SBS to 2D in order to stream SBS  so that you can either watch it in SBS mode (for 3d tvs) or 2d mode (left eye only) for normal watching
- Auto play state syncing and resuming
- Email notifications of new videos that match user watchlists appear on the server
- Report issue form
- Download transcoded videos
- TLS encryption
- Ability to detect whether the user is local or not, and redirect them to the internal ip of the server for streaming.
- Yahoo trailers before movies
- Ability to fast-seek to video location using keyframes.
- Thumbnail generation, and thumbnail preview for seeking
- Highcharts to display streaming metrics of users
- ffmpeg transcoder process management
- Support for "boost" initial transfer to pre-fill the buffer, then slows down transcoding to reduce cpu usage

Requirements:
--------------
- Windows Vista, 7, or 8 (64 bit)
- MySQL server
- XBMC instance running 24/7 (preferrably using MySQL backend)
- Python 2.7 (64 bit preferred)
- PIL (Python Imaging Library)
- Jinja2

Important Notices:
------------------
- All video files from XBMC need to be directly accessible locally from the machine running BRDFlix (can be done through network drive mapping). Direct smb support is not working.
- Browser must have flash enabled (except iPad)
- iPad HTTP Live Streaming (HLS) support sort of working
- Hardware decoding not enabled on flash, so computer running browser will need to be powerful enough to decode the stream
