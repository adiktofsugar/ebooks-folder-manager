#!/usr/bin/bash
set -eu
set -o pipefail

# this is intended to be called by cron
# it should rclone copy, then run efm, then rclone sync

local_dirpath="$1"
remote_spec="$2"

set -x

# we want to make local the same as remote first, so we don't upload random local files
rclone sync --progress "$remote_spec" "$local_dirpath" --exclude "efm.yaml"
poetry run efm --loglevel=debug "$local_dirpath"
rclone sync --progress "$local_dirpath" "$remote_spec" --exclude "efm.yaml"
