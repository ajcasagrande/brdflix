 select
         end_ms - start_ms as total_ms,
         end_bytes - start_bytes as total_bytes,
         stream_part.end_ms,
         (end_bytes - start_bytes) / 131072.0 / ((end_ms - start_ms) / 1000.0) as mbps,
         plays.id as play_id,
         stream.id as stream_id,
         stream_part.id as stream_part_id
 from plays
 join stream on stream.play_id = plays.id
 join stream_part on stream_part.stream_id = stream.id
 where plays.id
 and not stream.is_thumb
 and stream_part.end_ms is not null
 group by plays.id
