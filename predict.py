"""Finds and reads text in an image.

Usage:
  main.py TEXT_MASK IMAGE [--thresh=THRESH] [--debug]
  main.py (-h | --help)
  main.py --version

Options:
  --thresh=THRESH   Threshold for mask image [default: 200].
  --debug           Write debug output.
  -h --help         Show this screen.
  --version         Show version.
"""

import logging
import copy

import numpy as np
import cv2
from docopt import docopt
import pytesseract
from PIL import Image


RED = (0, 0, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)
BLACK = (0, 0, 0)

DEBUG = False


def cvToPIL(image):
    cv2_im = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(cv2_im)


def subimage(image, center, theta, width, height):
    theta *= np.pi / 180  # convert to rad

    v_x = (np.cos(theta), np.sin(theta))
    v_y = (-np.sin(theta), np.cos(theta))
    s_x = center[0] - v_x[0] * (width / 2) - v_y[0] * (height / 2)
    s_y = center[1] - v_x[1] * (width / 2) - v_y[1] * (height / 2)

    mapping = np.array([[v_x[0], v_y[0], s_x],
                        [v_x[1], v_y[1], s_y]])

    return cv2.warpAffine(image, mapping, (int(width), int(height)),
                          flags=cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REPLICATE)


def predict_text(mask, image, thresh):
    mask = cv2.imread(mask, cv2.CV_LOAD_IMAGE_GRAYSCALE)
    image = cv2.imread(image)

    # api = tesseract.TessBaseAPI()
    # api.Init(".", "eng", tesseract.OEM_DEFAULT)
    # api.SetPageSegMode(tesseract.PSM_AUTO)

    # tesseract.SetCvImage(image, api)
    # text = api.GetUTF8Text()
    # conf = api.MeanTextConf()
    # print text
    # api.End()

    h, w, _ = image.shape
    mask = cv2.resize(mask, (w, h))

    # add borders
    b = 12
    image = cv2.copyMakeBorder(image, b, b, b, b, cv2.BORDER_REPLICATE)
    mask = cv2.copyMakeBorder(mask, b, b, b, b,
                              cv2.BORDER_CONSTANT, value=BLACK)

    if DEBUG:
        dbg_img = copy.copy(image)

    if DEBUG:
        cv2.imshow('mask', mask)

    # print pytesseract.image_to_string(cvToPIL(image), config='-psm 3')

    # size = 2
    # kernel = np.ones((size, size), np.uint8)
    # mask = cv2.dilate(mask, kernel, iterations=1)

    # mask = cv2.erode(mask, kernel, iterations=1)

    # dilate + erosion

    # threshold the prediction
    _, mask = cv2.threshold(mask, thresh, 255, cv2.THRESH_BINARY)

    if DEBUG:
        cv2.imshow('mask thresh', mask)

    contours, hierarchy = cv2.findContours(mask,
                                           cv2.cv.CV_RETR_TREE,
                                           cv2.cv.CV_CHAIN_APPROX_SIMPLE)

    for contour in contours:
        # box = cv2.boundingRect(contour)
        # x, y, w, h = scale*np.array(box)
        # cv2.rectangle(image, (int(x), int(y)), (int(x+w), int(y+h)), RED, 3)

        rect = cv2.minAreaRect(contour)

        # increase size of rect
        dims = rect[1]
        dims = (dims[0]*1.1, dims[1]*1.1)
        rect = rect[0], dims, rect[2]

        if DEBUG:
            box = cv2.cv.BoxPoints(rect)
            box_np = np.int0(box)
            cv2.drawContours(dbg_img, [box_np], 0, (0, 0, 255), 2)

        center, (w, h), theta = rect
        patch = subimage(image, center, theta, w, h)
        for x in range(4):
            text = pytesseract.image_to_string(cvToPIL(patch))

            cv2.putText(dbg_img, text, (int(center[0]), int(10+center[1] + 7*x)), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.5, BLUE)
            # print text

            # cv2.imshow('patch', patch)
            # cv2.waitKey(0)

            patch = cv2.transpose(patch)
            patch = cv2.flip(patch, 0)

    if DEBUG:
        cv2.imshow('image', dbg_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Predictor 1.0')

    if arguments['--debug']:
        logging.basicConfig(level=logging.DEBUG)
        DEBUG = True

    predict_text(arguments['TEXT_MASK'], arguments['IMAGE'],
                 int(arguments['--thresh']))
