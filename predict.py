"""Finds and reads text in an image.

Usage:
  predict.py TEXT_MASK IMAGE [--thresh=THRESH] [--debug]
  predict.py (-h | --help)
  predict.py --version

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
# from skimage.restoration import denoise_tv_chambolle


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

    h, w, _ = image.shape
    mask = cv2.resize(mask, (w, h))

    # add borders
    b = 12
    image = cv2.copyMakeBorder(image, b, b, b, b, cv2.BORDER_REPLICATE)
    mask = cv2.copyMakeBorder(mask, b, b, b, b,
                              cv2.BORDER_CONSTANT, value=BLACK)

    # laplace = cv2.Laplacian(mask, cv2.CV_16S, ksize=3, scale=1, delta=0)
    # laplace = cv2.convertScaleAbs(laplace)
    # blur = cv2.GaussianBlur(mask, (5, 5), 0)
    # mask = cv2.addWeighted(mask, 1.5, blur, -0.5, 0)

    # idea is to increase separation but doesn't work
    # mask = denoise_tv_chambolle(mask, weight=10, n_iter_max=50)
    # mask = np.array(mask*255, np.uint8)

    if DEBUG:
        dbg_img = copy.copy(image)
        cv2.imshow('mask', mask)

    # print pytesseract.image_to_string(cvToPIL(image), config='-psm 3')

    # threshold the prediction
    _, thresh = cv2.threshold(mask, thresh, 255, cv2.THRESH_BINARY)

    # _, thresh = cv2.threshold(mask, 0, 255,
    #                         cv2.THRESH_BINARY+cv2.THRESH_OTSU)

    # dilate + erosion
    # size = 5
    # kernel = np.ones((size, size), np.uint8)
    # thresh = cv2.erode(thresh, kernel, iterations=1)
    # thresh = cv2.dilate(thresh, kernel, iterations=1)

    if DEBUG:
        cv2.imshow('thresh', thresh)
        # cv2.imwrite('thresholded.png', thresh)

    contours, hierarchy = cv2.findContours(thresh,
                                           cv2.cv.CV_RETR_LIST,
                                           cv2.cv.CV_CHAIN_APPROX_SIMPLE)

    for contour in contours:
        # box = cv2.boundingRect(contour)
        # x, y, w, h = scale*np.array(box)
        # cv2.rectangle(image, (int(x), int(y)), (int(x+w), int(y+h)), RED, 3)

        rect = cv2.minAreaRect(contour)

        # increase size of rect
        dims = rect[1]
        dims = (dims[0]*1.1, dims[1]*1.1)

        # snap rotation
        angles = [-360, -270, -180, -90, 0, 90, 180, 270, 360]
        theta = rect[2]
        epsylon = 5  # how large should the snap be
        for a in angles:
            if a-epsylon <= theta <= a+epsylon:
                theta = a

        rect = rect[0], dims, theta

        if DEBUG:
            box = cv2.cv.BoxPoints(rect)
            box_np = np.int0(box)
            cv2.drawContours(dbg_img, [box_np], 0, (0, 0, 255), 2)

        # skip OCR
        continue

        center, (w, h), theta = rect
        patch = subimage(image, center, theta, w, h)

        for x in range(4):
            text = pytesseract.image_to_string(cvToPIL(patch))

            cv2.putText(dbg_img, text, (int(center[0]), int(10+center[1] + 7*x)), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.6, BLUE)
            print text

            # cv2.imshow('patch', patch)
            # cv2.waitKey(0)

            patch = cv2.transpose(patch)
            patch = cv2.flip(patch, 0)

        print "======"

    if DEBUG:
        cv2.imshow('image', dbg_img)
        cv2.imwrite('text-debug.png', dbg_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Predictor 1.0')

    if arguments['--debug']:
        logging.basicConfig(level=logging.DEBUG)
        DEBUG = True

    predict_text(arguments['TEXT_MASK'], arguments['IMAGE'],
                 int(arguments['--thresh']))
