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
  label_gen.py read-s3 S3-IN-BUCKET S3-FILE S3-OUT-BUCKET S3-PATH [--use-ramdisk] [--debug] [--dbg-image]
  label_gen.py read FILE PATH [--debug] [--dbg-image]
  label_gen.py (-h | --help)
  label_gen.py --version

Options:
  --use-ramdisk   Store temporary files in /tmp/ram/.
  --debug         Write debug output.
  --dbg-image     Create a debug label.
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


def run_local(pdf_file, path, debug_image, flat):
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
    subprocess.call(['pdffigures/pdffigures', '-j',
                    outident_json, filepath], stdout=DEVNULL, stderr=DEVNULL)

    json_files = []
    img_files = []
    label_files = []

    logging.debug("Finished. Now look for the JSON and generate labels.")

    # pdffigures now generates only a singe JSON file, we need one file per figure
    # https://github.com/allenai/pdffigures/commit/8ffcaceab3fdc97ec489c58e87191b7e12c0134a

    json_file = '{}.json'.format(outident_json)

    if os.path.isfile(json_file):
        with open(json_file) as fh:
            figures = json.load(fh)


            logging.debug('Found {} figures'.format(len(figures)))

            for index, figure in enumerate(figures):
                chart_json = '{}-Figure-{}.json'.format(outident_json, index)
                json_files.append(chart_json)

                with open(chart_json, 'w') as jfh:
                    json.dump(figure, jfh)

                def image_path(factor):
                    ext = '' if factor == 1 else '-{}x'.format(factor)
                    name = '{}-Figure-{}{}.png'.format(ident, index, ext)
                    return os.path.join(img_path, name)

                # render image with different resolutions
                for factor in [1, 2]:
                    image_file = image_path(factor)
                    logging.debug('Render image {} from {}'.format(
                        image_file, filepath))

                    render.render_chart(filepath, figure['Page']-1,
                                        figure['ImageBB'],
                                        int(factor*100), image_file)
                    img_files.append(image_file)

                # labeled image
                output = os.path.join(
                    label_path, '{}-Figure-{}-label.png'.format(
                        ident, index, factor))
                dbg_output = None
                if debug_image:
                    dbg_output = os.path.join(
                        label_path, '{}-Figure-{}-dbg.png'.format(
                            ident, index, factor))

                logging.debug('generate label {}'.format(output))
                if label_image.gen_labeled_image(
                        figure, image_path(1), output, dbg_output, DEBUG):
                    # yes, a labeled file was generated
                    label_files.append(output)
                    if dbg_output:
                        label_files.append(dbg_output)

        # remove the one json file with data for all figures
        os.remove(json_file)

    return json_files, img_files, label_files


def run_s3(in_bucket_name, filename, out_bucket_name, path, ramtemp, debug_image):
    conn = S3Connection(config.access_key, config.secret_key, is_secure=False)
    in_bucket = conn.get_bucket(in_bucket_name)
    out_bucket = conn.get_bucket(out_bucket_name)

    dirpath = tempfile.mkdtemp(dir='/tmp/ram/' if ramtemp else None)
    logging.debug('Temp directory in {}'.format(dirpath))

    try:
        # copy into temp
        key = Key(in_bucket, filename)
        target = os.path.join(dirpath, os.path.basename(filename))
        key.get_contents_to_filename(target)

        # run algos
        files = run_local(target, dirpath, debug_image, True)

        # write files back to s3
        for f in files[0]:
            key = Key(out_bucket, os.path.join(path, 'json', os.path.basename(f)))
            key.set_contents_from_filename(f)
        for f in files[1]:
            key = Key(out_bucket, os.path.join(path, 'img', os.path.basename(f)))
            key.set_contents_from_filename(f)
        for f in files[2]:
            key = Key(out_bucket, os.path.join(
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
        run_s3(arguments['S3-IN-BUCKET'], arguments['S3-FILE'],
               arguments['S3-OUT-BUCKET'], arguments['S3-PATH'],
               arguments['--use-ramdisk'], arguments['--dbg-image'])
    elif arguments['read']:
        run_local(arguments['FILE'], arguments['PATH'],
                  arguments['--dbg-image'], False)
