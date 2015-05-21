"""Find bad figures

Reads all JSON files in an S3 bucket and generates a list of files that are
probably not good labels. A bad label is a label with very few or very many
text boxes. This could happen if an image is used as a figure with text that
is not embedded in the PDF. To avoid false negatives, we should exclude
those even if they have a little bit of text in  them from for example a
caption or some other text in the document.

Criteria for exclusion:
 - no or very few labels
 - only text close to the border
 - almost all of the picture is white

Usage:
  main.py read-s3 S3-BUCKET S3-PATH [--debug]
  main.py read PATH [--debug]
  main.py check FILE [--debug]
  main.py (-h | --help)
  main.py --version

Options:
  --debug         Write debug output.
  -h --help       Show this screen.
  --version       Show version.
"""

import os
import re
import logging
import json

from docopt import docopt
from boto.s3.connection import S3Connection

import config

PATTERN = re.compile('(.*-Figure-[0-9]+).*\.json')


# true if a is in b
def contains(a, b):
    return (a[0] > b[0] and a[2] < b[2] and
            a[1] > b[1] and a[3] < b[3])


def area(a):
    return (a[2] - a[0]) * (a[3] - a[1])


def all_in_border(bounds, texts):
    """ Returns true if all text is either in upper or lower border area. """
    x0, y0, x1, y1 = bounds
    h = y1 - y0

    not_top_border = [x0, y0 + h*0.05,
                      x1, y1]
    not_bottom_border = [x0, y0,
                         x1, y1 - h*0.05]

    top = False
    bottom = False

    for text in texts:
        if contains(text['TextBB'], not_top_border):
            top = True

        if contains(text['TextBB'], not_bottom_border):
            bottom = True

        if top and bottom:
            return False

    return True


def is_sum_larger(max_area, texts):
    sum_so_far = 0
    for text in texts:
        sum_so_far += area(text['TextBB'])
        if sum_so_far > max_area:
            return True
    return False


def check(json_data):
    data = json.loads(json_data)
    texts = data['ImageText']

    # no text at all
    if len(texts) == 0:
        logging.debug("No text")
        return True

    # very little text
    if len(texts) == 1:
        logging.debug("One text label")
        return True

    # all the text is within the border area (probably an artifact)
    if all_in_border(data['ImageBB'], texts):
        logging.debug("All text is in upper or lower border")
        return True

    # almost the whole image is text
    # use crude implementation where we just sum up the text area
    # and kick something out if >50% is text
    a = area(data['ImageBB'])
    if is_sum_larger(a*0.5, texts):
        logging.debug("Almost everything is text")
        return True

    return False


def run_s3(bucket_name, path):
    conn = S3Connection(config.access_key, config.secret_key, is_secure=False)
    bucket = conn.get_bucket(bucket_name)

    for key in bucket.list(path):
        if os.path.splitext(key.name)[1] == '.json':
            if check(key.get_contents_as_string()):
                groups = PATTERN.search(key.name)
                if groups:
                    print groups.group(1)


def run_local(path):
    for name in os.listdir(path):
        json_file = os.path.join(path, name)
        if os.path.isfile(json_file):
            if os.path.splitext(name)[1] == '.json':

                with open(json_file) as f:
                    if check(f.read()):
                        groups = PATTERN.search(name)
                        if groups:
                            print groups.group(1)


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Rater 1.0')

    if arguments['--debug']:
        logging.basicConfig(level=logging.DEBUG)

    if arguments['read-s3']:
        run_s3(arguments['S3-BUCKET'], arguments['S3-PATH'])
    elif arguments['read']:
        run_local(arguments['PATH'])
    elif arguments['check']:
        with open(arguments['FILE']) as f:
            print "Bad label" if check(f.read()) else "Good label"
