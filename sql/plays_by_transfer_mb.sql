select
	stream.quality_id,
	sum(stream.transfer_size / 1048576) as total_mb,
	sum(unix_timestamp(stream.end_time) - unix_timestamp(stream.start_time)) as total_time,
	(sum(stream.transfer_size / 1048576) * 8 / sum(unix_timestamp(stream.end_time) - unix_timestamp(stream.start_time))) as avg_mbps,
	plays.*
from plays
inner join stream on stream.play_id = plays.id
where not stream.is_thumb and stream.transfer_size is not null
group by plays.id
order by start_time asc