select known_host.name, 
		 request.ip_address, 
		 request.port,
		 max(request.timestamp) as last_access,
		 count(*) as total_requests,
		 group_concat(distinct user.username order by user.username) as users
from request
left join known_host on known_host.ip_address = request.ip_address
left join user on user.id = request.user_id
group by request.ip_address, request.port, user.username
order by total_requests desc