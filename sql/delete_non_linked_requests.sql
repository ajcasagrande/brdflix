-- This will delete all requests older than XXX days
-- that do not have a foreign key pointing to them 
-- (currently only watch and stream tables)
delete request from request
left join play on play.request_id = request.id
left join stream on stream.request_id = request.id
where play.id is null 
and stream.id is null
and request.timestamp < now() - interval 10 day
