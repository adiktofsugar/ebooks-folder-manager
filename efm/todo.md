There are 2 main issues I currently have:

# Files
All the dedrm stuff and the reformat pdf actions create a new file.
Since things can go wrong, I'd like to keep a backup.

I think a good way to handle this would be to generate a set of actions and say an action "always" generates a new file (rename may be a special case). We should also copy/move the original file to "original.epub". We'll put these files into a folder named after the original name of the file in a temporary directory defined by the config file.

So, as an example, if we have a file "1q84.epub", we copy it to '/tmp/1q84_epub/original.epub', then run remove_drm to output to "after_remove_drm.epub", then "reformat" outputs to "after_reformat.epub", then maybe we just copy it to "final.epub", and then remove the 1q84.epub file and copy "final.epub" to the new name.

Issues:
- could be slow?
- takes a lot of space? ...these are pretty small file though
- i know k2pdfopt uses the filename for some metadata, so naming them weird things could result in odd stuff like this

For the "filename is important" one...maybe we call the current final one the actual filename instead. So in the example above, we'd initially copy it to "1q84.epub", then remove drm to whatever file, rename the original to "original.epub" and the drm free one "1q84.epub", etc.

Note: This means each action would have a final filename, rather than just in the Book class

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