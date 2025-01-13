import cherrypy
import json
import time
from datetime import datetime

import brdflix
from db_mysql import DEFAULT as db
from datatypes import *
from decorators import *
from helpers import *
from transcode import *

class ChartsInterface:
    _cp_config = { 'tools.log_request.on': False,
                   'tools.login_required.on': True }
                   
    @cherrypy.expose
    def user_mb(self):
        query = '''
            select
            from_unixtime(floor(end_ms / 1000 / 60)*60) as `timestamp`,
            sum(end_bytes - start_bytes) / 1024 / 1024 as total_mb
            from stream_part
            join stream on stream.id = stream_id
            where stream.user_id = %s
            and from_unixtime(end_ms / 1000) > date_sub(now(), interval 1 day)
            group by floor(end_ms / 1000 / 60)
            order by `timestamp` asc
        '''
        user_id = 1
        rows = db.fetch_all(query, (int(user_id),))

    @cherrypy.expose
    def all_mb(self):
        query = '''
            select
            from_unixtime(floor(end_ms / 1000 / 60)*60) as `timestamp`,
            stream.user_id,
            sum(end_bytes - start_bytes) / 1024 / 1024 as total_mb
            from stream_part
            join stream on stream.id = stream_id
            where from_unixtime(end_ms / 1000) > date_sub(now(), interval 1 day)
            group by stream.user_id, floor(end_ms / 1000 / 60)
            order by `timestamp` asc
        '''
        rows = db.fetch_all(query)

    @cherrypy.expose
    def stream_parts(self, stream_id):
        data = []
        query = '''
                select end_ms,
                    (end_bytes - start_bytes) / 131072.0 / ((end_ms - start_ms) / 1000.0) as mbps
                from stream_part
                where stream_id = %s
        '''
        rows = db.fetch_all(query, (int(stream_id),))
        for row in rows:
            data.append( [ int(round(row['end_ms'] / 1000.0)), float(row['mbps']) ] )
        ser = {'name': "Stream " + str(stream_id), 'data': data }
        return ser

    @cherrypy.expose
    def stream_chart_data(self):
        series = []
        for p in ACTIVE_PROCESSES:
            if p.stream_obj and p.stream_obj.id:
                series.append(self.stream_parts(p.stream_obj.id))
        return json.dumps({ "series": series })

    @cherrypy.expose
    def stream_chart(self):
        t, j = get_jinja_template("stream_chart.html")
        j.chart_series = []
        for p in ACTIVE_PROCESSES:
            if p.stream_obj and p.stream_obj.id:
                j.chart_series.append(self.stream_parts(p.stream_obj.id))
        return t.render(j.kwargs())

    @cherrypy.expose
    def play_chart(self, play_id):
        t, j = get_jinja_template("stream_chart.html")
        j.chart_series = [ self.play_details(play_id) ]
        j.play_id = play_id
        return t.render(j.kwargs())

    @cherrypy.expose
    def play_details_json(self, play_id, max_points=25):
        return json.dumps({ "series": self.play_details(play_id) })

    @cherrypy.expose
    def play_details(self, play_id, max_points=25):
        query = '''
                select
                        end_ms - start_ms as total_ms,
                        end_bytes - start_bytes as total_bytes,
                        stream_part.end_ms,
                        (end_bytes - start_bytes) / 131072.0 / ((end_ms - start_ms) / 1000.0) as mbps,
                        play.id as play_id,
                        stream.id as stream_id,
                        stream_part.id as stream_part_id
                from play
                join stream on stream.play_id = play.id
                join stream_part on stream_part.stream_id = stream.id
                where play.id = %s
                and stream_part.end_ms is not null
        '''
        rows = db.fetch_all(query, (int(play_id),))
        streams = {}
        for row in rows:
            stream_id = row["stream_id"]
            if not stream_id in streams.keys():
                streams[stream_id] = []
            streams[stream_id].append([ int(round(row['end_ms'] / 1000.0)), float(row['mbps']) ])
        ser = []
        for key, val in streams.items():
            ser.append({"name": "Stream " + str(key), "data": val })
        return ser

    @cherrypy.expose
    def play_details_old(self, play_id, max_points=25):
        data = []
        query = '''
                select
                        end_ms - start_ms as total_ms,
                        end_bytes - start_bytes as total_bytes,
                        stream_part.end_ms,
                        (end_bytes - start_bytes) / 131072.0 / ((end_ms - start_ms) / 1000.0) as mbps,
                        play.id as play_id,
                        stream.id as stream_id,
                        stream_part.id as stream_part_id
                from play
                join stream on stream.play_id = play.id
                join stream_part on stream_part.stream_id = stream.id
                where play.id = %s
                and stream_part.end_ms is not null
        '''
        rows = db.fetch_all(query, (int(play_id),))
        for row in rows:
            data.append( [ int(round(row['end_ms'] / 1000.0)), float(row['mbps']) ] )
        ser = {'name': "Play " + str(play_id), 'data': data }


#        ms = 0
#        total = 0.0
#        count = 0
#        interval = int(round(len(data) / int(max_points)))
#        if interval < 1:
#            interval = 1
#        d2 = []
#        for i in range(len(data)):
#            ms = data[i][0]
#            total += data[i][1]
#            count += 1
#            i += 1
#            if i % interval == 0:
#                d2.append([ms, total / count])
#                count = 0
#                total = 0.0
#                ms = 0
#        if count > 0:
#            d2.append([ms, total / count])
#        ser = {'name': "Play " + str(play_id), 'data': d2 }

        return ser

    @cherrypy.expose
    def all_plays(self, limit=5):
        t, j = get_jinja_template("all_plays.html")
        query = "select * from `play` join media on media.id = `play`.media_id join request on request.id = play.request_id order by start_time desc limit %s;"
        j.plays = Play().raw_query_all(query, (int(limit),), include_extras=True)
        j.series = {}
        for play in j.plays:
            j.series[play.id] = [ self.play_details(play.id) ]
        return t.render(j.kwargs())

    @cherrypy.expose
    def active_streams_json(self, seconds_ago=7200):
        query = '''
        select
           end_ms - start_ms as total_ms,
           end_bytes - start_bytes as total_bytes,
           stream_part.end_ms,
           (end_bytes - start_bytes) / 131072.0 / ((end_ms - start_ms) / 1000.0) as mbps,
           stream.play_id as play_id,
           stream.id as stream_id,
           stream_part.id as stream_part_id,
           media.fname as fname
        from stream
        join stream_part on stream_part.stream_id = stream.id
        join media on media.id = stream.media_id
        where stream_part.end_ms is not null
        and stream_part.end_ms >= %s
        order by stream_part.end_ms asc
        '''
        rows = db.fetch_all(query, (int(round(time.time() * 1000))-(seconds_ago*1000),))
        my_rows = {}
        for row in rows:
            if not row['stream_id'] in my_rows:
                my_rows[row['stream_id']] = []
            my_rows[row['stream_id']].append(row)
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps(my_rows, cls=DecimalEncoder)

    @cherrypy.expose
    def d3(self):
        t, j = get_jinja_template('d3.html')
        return t.render(j.kwargs())

