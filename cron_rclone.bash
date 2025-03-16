#!/usr/bin/bash
set -eu
set -o pipefail

# this is intended to be called by cron
# it should rclone copy, then run efm, then rclone sync

local_dirpath="$1"
remote_spec="$2"

set -x
rclone copy --progress "$remote_spec" "$local_dirpath" 
poetry run efm --loglevel=debug "$local_dirpath"
rclone sync --progress "$local_dirpath" "$remote_spec" --exclude "efm.yaml"
