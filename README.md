I'm tired of calibre. All I want is to add minimal metadata to my books and keep them in a folder.

# This is totally not ready for real use

I can't even really use it yet. At least not all the time. So if this is something you really want, check back in a little while later.

# How to use to make a cloud library

So far, this is what I'm doing on linux:
- get [rclone](https://rclone.org/)
- set up your google drive account as "googledrive"
- make a folder in your drive as "ebooks"
- dump your ebooks in there
- run `rclone sync --progress googledrive:ebooks ~/ebooks`
- run `poetry run efm ~/ebooks` (with your home config set to whatever actions you want to run)
- run `rclone sync --progress ~/ebooks googledrive:ebooks`

This works, but since I'm not sure what's going to break it I'm doing it all very carefully (aka I'm using `-i` for the rclone commands). When I'm more confident, I'll make a systemd unit and timer file to run this script every so often.

# Planned Limitations

## Multiple formats

Multiple formats for a single ebook are not supported. As in, if you have the same book in epub and pdf, they will always be 2 separate entites in this project, since this is designed to manage files.

## Sync to device

ebooks generally mount as a drive when connected to your computer, and then you can drag them over. I don't want to put in any effort to solve that in this project.

## Others...

...will be added as they are learned.

# Unplanned Limitations

## Books that have more than one output file

Apparently "topaz" books have an svg zip output. That's not supported because the whole thing assumes one file. That may not always be the case but for now it is.