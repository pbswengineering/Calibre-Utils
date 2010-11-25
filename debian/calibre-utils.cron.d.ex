#
# Regular cron jobs for the calibre-utils package
#
0 4	* * *	root	[ -x /usr/bin/calibre-utils_maintenance ] && /usr/bin/calibre-utils_maintenance
