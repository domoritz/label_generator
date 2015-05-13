"""Figure extractor and label generator

Read a single PDF file and write the extracted data and labels
to a directory with the following structure:

 /json
   - filename_figno.json
 /img
   - filename_figno.png
   - filename_figno_2x.png (200 DPI)
   - filename_figno_3x.png (300 DPI)
   - filename_figno_4x.png (400 DPI)
 /text-masted
  - filename_figno_box.png
  - filename_figno_mask.png

Usage:
  main.py read-s3 S3-FILE S3-PATH
  main.py read FILE PATH
  main.py (-h | --help)
  main.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.
"""

import tempfile
import shutil

from docopt import docopt
from boto.s3.connection import S3Connection

import config


def run_local(pdf_file, path):
    print pdf_file, path


def run_s3(conn):
    conn = S3Connection(config.access_key, config.secret_key)

    print conn

if __name__ == '__main__':
    arguments = docopt(__doc__, version='Extractor 1.0')

    dirpath = tempfile.mkdtemp()

    print arguments

    try:
        if arguments['read-s3']:
            run_s3(arguments)
        elif arguments['read']:
            run_local(arguments['FILE'], arguments['PATH'])
        else:
            print "Unknown option"
    finally:
        shutil.rmtree(dirpath)
