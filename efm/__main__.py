import argparse


usage = '''
efm [-h][--dry][--watch][--loglevel=debug|info|error][--adobekey=<adobekey>] <folder> [<action> ...]
-h        help
--dry     print what each action would do without actually doing it
--watch   watch folder for changes
--loglevel  <loglevel> set log level (default: info)
--adobekey  <adobekey> path to Adobe key file for use with dedrm of adobe-DRM'd files

<action>  is one of:
  - drm           remove DRM from files (backs up original as .bak)
  - rename        rename files based on metadata
  - print         print metadata to console
  - pdf           reformat a PDF via k2pdfopt (backs up original as .bak)
  - none          do nothing (useful for testing to see if we don't throw any errors)

Run efm on folder. This will walk that folder recursively and perform all actions you specify.
If no actions are specified, will use any efm.(yaml|yml|json|jsonc) files in the folder.
'''

def main():
  argparser = argparse.ArgumentParser(add_help=True, usage=usage)
  argparser.add_argument('folder', help='folder to process')
  argparser.add_argument('action', 
                         nargs='*',
                         choices=['drm', 'rename', 'print', 'pdf', 'none'], 
                         help='action to perform')
  argparser.add_argument('--dry', action='store_true', help='dry run')
  argparser.add_argument('--watch', action='store_true', help='watch folder for changes')
  argparser.add_argument('--loglevel', help='log level')
  argparser.add_argument('--adobekey', help='path to Adobe key file')
  args = argparser.parse_args()
  print(args)
