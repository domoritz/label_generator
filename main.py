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
 /text-masked
  - filename_figno_box.png
  - filename_figno_mask.png

Usage:
  main.py read-s3 S3-BUCKET S3-FILE S3-PATH [--use-ramdisk] [--debug]
  main.py read FILE PATH  [--debug]
  main.py (-h | --help)
  main.py --version

Options:
  --use-ramdisk   Store temporary files in /tmp/ram/
  --debug         Create debug output
  -h --help       Show this screen.
  --version       Show version.
"""

import tempfile
import shutil
import subprocess
import os
import json
import logging

from docopt import docopt
from boto.s3.connection import S3Connection
from boto.s3.key import Key

import config
import render
import label_image


DEBUG = False


def create_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def run_local(pdf_file, path, flat):
    filepath = os.path.abspath(pdf_file)
    outpath = os.path.abspath(path)

    ident = os.path.splitext(os.path.basename(pdf_file))[0]

    if flat:
        # cheaper because we don't need separate directories
        json_path = outpath
        img_path = outpath
        label_path = outpath
    else:
        json_path = os.path.join(outpath, 'json')
        img_path = os.path.join(outpath, 'img')
        label_path = os.path.join(outpath, 'text-masked')

        # create directories, if needed
        create_dir(json_path)
        create_dir(img_path)
        create_dir(label_path)

    outident_json = os.path.join(json_path, ident)

    # generate the json for figures
    logging.debug('Run pdffigures {}'.format(filepath))
    DEVNULL = open(os.devnull, 'w')
    subprocess.check_call(['pdffigures/pdffigures', '-j',
                           outident_json, filepath], stderr=DEVNULL)

    json_files = []
    img_files = []
    label_files = []

    index = 1
    while True:
        chart_json = '{}-{}.json'.format(outident_json, index)
        if not os.path.isfile(chart_json):
            break

        json_files.append(chart_json)

        with open(chart_json) as fh:
            parsed = json.load(fh)

            def image_path(factor):
                ext = '' if factor == 1 else '-{}x'.format(factor)
                name = '{}-{}{}.png'.format(ident, index, ext)
                return os.path.join(img_path, name)

            # render image with different resolutions
            for factor in [1, 2]:
                image_file = image_path(factor)
                logging.debug('Render image {}'.format(image_file))
                render.render_chart(filepath, parsed['Page']-1,
                                    parsed['ImageBB'],
                                    int(factor*100), image_file)
                img_files.append(image_file)

            # labeled image
            output = os.path.join(
                label_path, '{}-{}-label.png'.format(ident, index, factor))
            dbg_output = None
            if DEBUG:
                dbg_output = os.path.join(
                    label_path, '{}-{}-dbg.png'.format(
                        ident, index, factor))

            logging.debug('generate label {}'.format(output))
            if label_image.gen_labeled_image(
                    parsed, image_path(1), output, dbg_output):
                # yes, a labeled file was generated
                label_files.append(output)
                if dbg_output:
                    label_files.append(dbg_output)

        index += 1

    logging.debug('Found {} figures'.format(index - 1))

    return json_files, img_files, label_files


def run_s3(bucket_name, filename, path, ramtemp):
    conn = S3Connection(config.access_key, config.secret_key, is_secure=False)
    bucket = conn.get_bucket(bucket_name, validate=True)

    dirpath = tempfile.mkdtemp(dir='/tmp/ram/' if ramtemp else None)
    logging.debug('Temp directory in {}'.format(dirpath))

    try:
        # copy into temp
        key = Key(bucket, filename)
        target = os.path.join(dirpath, os.path.basename(filename))
        key.get_contents_to_filename(target)

        # run algos
        files = run_local(target, dirpath, True)

        # write files back to s3
        for f in files[0]:
            key = Key(bucket, os.path.join(path, 'json', os.path.basename(f)))
            key.set_contents_from_filename(f)
        for f in files[1]:
            key = Key(bucket, os.path.join(path, 'img', os.path.basename(f)))
            key.set_contents_from_filename(f)
        for f in files[2]:
            key = Key(bucket, os.path.join(
                path, 'text-masked', os.path.basename(f)))
            key.set_contents_from_filename(f)
    finally:
        shutil.rmtree(dirpath)


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Extractor 1.0')

    if arguments['--debug']:
        DEBUG = True
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("boto").setLevel(logging.WARNING)

    if arguments['read-s3']:
        run_s3(arguments['S3-BUCKET'], arguments['S3-FILE'],
               arguments['S3-PATH'], arguments['--use-ramdisk'])
    elif arguments['read']:
        run_local(arguments['FILE'], arguments['PATH'], False)
    else:
        print "Unknown option"
