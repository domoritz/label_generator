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
import subprocess
import os
import json

from docopt import docopt
from boto.s3.connection import S3Connection

import config
import render
import label_image


def create_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def run_local(pdf_file, path):
    filepath = os.path.abspath(pdf_file)
    outpath = os.path.abspath(path)

    ident = os.path.splitext(os.path.basename(pdf_file))[0]

    json_path = os.path.join(outpath, 'json')
    img_path = os.path.join(outpath, 'img')
    label_path = os.path.join(outpath, 'text-masked')

    outident_json = os.path.join(json_path, ident)

    # create directories
    create_dir(json_path)
    create_dir(img_path)
    create_dir(label_path)

    # generate the json for figures
    subprocess.check_call(["pdffigures/pdffigures", "-j",
                           outident_json, filepath])

    index = 1
    while True:
        chart_json = '{}-Figure-{}.json'.format(outident_json, index)
        if not os.path.isfile(chart_json):
            break

        with open(chart_json) as fh:
            parsed = json.load(fh)

            def image_path(factor):
                ext = '' if factor == 1 else '-{}x'.format(factor)
                name = '{}-Figure-{}{}.png'.format(ident, index, ext)
                return os.path.join(img_path, name)

            # render image with different resolutions
            for factor in [1, 2]:
                render.render_chart(filepath, parsed['Page']-1,
                                    parsed['ImageBB'],
                                    int(factor*100), image_path(factor))

            # labeled image
            output = os.path.join(
                label_path, '{}-Label-{}.png'.format(ident, index, factor))
            dbg_output = os.path.join(
                label_path, '{}-Label-{}-dbg.png'.format(ident, index, factor))
            label_image.gen_labeled_image(parsed, image_path(1), output, dbg_output)

        index += 1


def run_s3(conn):
    conn = S3Connection(config.access_key, config.secret_key)

    dirpath = tempfile.mkdtemp()
    try:
        print conn

        # copy into temp

        # run algos

        # write files back to s3
    finally:
        shutil.rmtree(dirpath)


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Extractor 1.0')

    if arguments['read-s3']:
        run_s3(arguments)
    elif arguments['read']:
        run_local(arguments['FILE'], arguments['PATH'])
    else:
        print "Unknown option"
