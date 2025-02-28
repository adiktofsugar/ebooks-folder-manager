The only open source DRM removal software I've been able to find is https://github.com/noDRM/DeDRM_tools.

It's packaged as a calibre plugin, but it's basically just a bunch of python scripts that do pretty specific things, although the configuration is based on a json file saved in the calibre plugins folder.

That said, it _should_ be usable, but certain things that are hard to do with that plugin remain hard to do while using it outside the plugin.

# How to use

Since this project is node, we'd need to use a subprocess, and can output a bunch of instructions since this is pretty manual. Likely we'd just get instructions for how to configure everything. Since the config is based on a json file we should still be able to reuse most of it without calibre, though.

# Adobe Digital Editions - Linux

Adobe Digital Editions only works on windows or mac. There are scripts in DeDRM tools that find the user key for that program on windows or mac. To use linux, you need to run ADE in wine, then run the script that find it for windows under wine, so you end up needing two pythons, which is...weird.

- install wine
- install ADE via wine (open .exe file)
- activate ADE
- install python 3 via wine (open .msi file)
- install pycryptodome library via wine `wine pip install pycryptodome`
- run script via wine `wine python adobekey.py`

That should output the key (.der file). Once you have that you can add it to the plugin config and save it, but keep in mind it's just a path.
