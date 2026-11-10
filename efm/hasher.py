"""What a store hash looks like. See todo/hasher.md for moving the hashing itself here."""

import re

HASH_PREFIX = "xx_"
HASH_PATTERN = re.compile(r"xx_[0-9a-f]{32}")
