python based watch util - https://pypi.org/project/watchdog/#description
rust based watch util - https://github.com/watchexec/watchexec
watchman - https://facebook.github.io/watchman/

# to watch or not to watch
I'm not sure I care about supporting watching. I can just run the command on a cron since its idempotent. The main advantage to watching is that I could run it on only one file, which is maybe faster. I think that you could just use a watching program to run this, though...as long as it supports running on single files...