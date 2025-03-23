#!/usr/bin/env python3
# -*- coding: utf-8 -*-


#@@CALIBRE_COMPAT_CODE_START@@
import sys, os

# Explicitly allow importing everything ...
if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Bugfix for Calibre < 5:
if "calibre" in sys.modules and sys.version_info[0] == 2:
    from calibre.utils.config import config_dir
    if os.path.join(config_dir, "plugins", "DeDRM.zip") not in sys.path:
        sys.path.insert(0, os.path.join(config_dir, "plugins", "DeDRM.zip"))

# Explicitly set the package identifier so we are allowed to import stuff ...
#__package__ = "DeDRM_plugin"

#@@CALIBRE_COMPAT_CODE_END@@

from ignoblekeyGenPassHash import generate_key
import sys

__license__ = 'GPL v3'

DETAILED_MESSAGE = \
'You have personal information stored in this plugin\'s customization '+ \
'string from a previous version of this plugin.\n\n'+ \
'This new version of the plugin can convert that info '+ \
'into key data that the new plugin can then use (which doesn\'t '+ \
'require personal information to be stored/displayed in an insecure '+ \
'manner like the old plugin did).\n\nIf you choose NOT to migrate this data at this time '+ \
'you will be prompted to save that personal data to a file elsewhere; and you\'ll have '+ \
'to manually re-configure this plugin with your information.\n\nEither way... ' + \
'this new version of the plugin will not be responsible for storing that personal '+ \
'info in plain sight any longer.'

def uStrCmp (s1, s2, caseless=False):
    import unicodedata as ud
    if sys.version_info[0] == 2:
        str1 = s1 if isinstance(s1, unicode) else unicode(s1)
        str2 = s2 if isinstance(s2, unicode) else unicode(s2)
    else: 
        str1 = s1 if isinstance(s1, str) else str(s1)
        str2 = s2 if isinstance(s2, str) else str(s2)

    if caseless:
        return ud.normalize('NFC', str1.lower()) == ud.normalize('NFC', str2.lower())
    else:
        return ud.normalize('NFC', str1) == ud.normalize('NFC', str2)

def parseCustString(keystuff):
    userkeys = []
    ar = keystuff.split(':')
    for i in ar:
        try:
            name, ccn = i.split(',')
            # Generate Barnes & Noble EPUB user key from name and credit card number.
            userkeys.append(generate_key(name, ccn))
        except:
            pass
    return userkeys
