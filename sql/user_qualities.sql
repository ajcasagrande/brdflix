select * from quality, user
where (user.admin = 1 and quality.admin_only = 1) or quality.admin_only = 0
order by bitrate, width