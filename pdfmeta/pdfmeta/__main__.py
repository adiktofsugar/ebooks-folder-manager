from argparse import ArgumentParser
import shutil
import tempfile
import pymupdf
import json

def main():
    parser = ArgumentParser()
    parser.add_help = True
    parser.add_argument('pdf_file', type=str, help='path to the PDF file')
    parser.add_argument('value', nargs='?', type=str, help='JSON encoded value to set')
    args = parser.parse_args()

    pdf = pymupdf.open(args.pdf_file)
    if args.value is not None:
        if "__ebooks-folder-manager.json" in pdf.embfile_names():
          pdf.embfile_del('__ebooks-folder-manager.json')
        pdf.embfile_add('__ebooks-folder-manager.json', args.value.encode('utf-8'))
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
          pdf.save(tmp.name)
          shutil.move(tmp.name, args.pdf_file)
    else:
      if "__ebooks-folder-manager.json" in pdf.embfile_names():
        print(pdf.embfile_get('__ebooks-folder-manager.json').decode('utf-8'))
      else:
        print("{}")
    