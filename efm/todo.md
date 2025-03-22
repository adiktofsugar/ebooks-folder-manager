
# DeDRM plugin
Trying to get this to work without changing the DeDRM plugin files is difficult because of how they're written. We should probably be interacting with them more like external processes, but there's a lot of calibre / config specific stuff in there.

I have 2 basic ideas:
- change them all to be more generic scripts
- simulate "calibre" and the "config" so they work as-is

## Make more generic
maybe they'll even merge it back to main, which would be nice. but unlikely. or would require a ton of work from me.
this would require me to understand the scripts, likely change a lot of the inputs, which could make it less efficient, but give me much more control over where all the files are.
the main benefit for this is that I can make my own flow.
the main downside is that upgrading will require close attention to the diff.

## Simulate calibre
this lets them work as-is, meaning the scope is still assumed to be "calibre plugin", which isn't how this is used, so there will probably be some issues arising from that (like how to get the keys, messaging, storing driver files, etc.)

the main benefit is I don't have to understand them very well (unless something goes wrong) and if they ever get updated it should be the same as "installing a new version of the plugin", which is nice.