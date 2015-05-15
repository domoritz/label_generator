import json
import math
import sys

import numpy as np
import cv2

WHITE = (255, 255, 255)
RED = (0, 0, 255)
factor = 1


def gen_labeled_image(description, image, target, debug=None):
    bounds = np.array(description['ImageBB'])

    bounds *= factor

    x0 = bounds[0]
    y0 = bounds[1]
    w = bounds[2] - x0
    h = bounds[3] - y0

    chart = cv2.imread(image, cv2.CV_LOAD_IMAGE_GRAYSCALE)
    # h, w = chart.shape

    texts = description['ImageText']

    if len(texts) == 0:
        print """No text boxes in chart. Since this could mean that the image
            does not have embedded text, we are ignoring it."""
        return

    label = np.zeros((h, w), np.uint8)

    for text_box in texts:
        tb = np.array(text_box['TextBB'])
        tb *= factor

        tx0 = int(math.floor(tb[0] - x0))
        ty0 = int(math.floor(tb[1] - y0))
        tx1 = int(math.ceil(tb[2] - x0))
        ty1 = int(math.ceil(tb[3] - y0))

        # label exactly the text
        # patch = chart[ty0:ty1, tx0:tx1]
        # ret, patch = cv2.threshold(patch, 0, 255,
        #                            cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
        # label[ty0:ty1, tx0:tx1] = patch

        # label a box around the text
        cv2.rectangle(label, (tx0, ty0), (tx1, ty1), WHITE, cv2.cv.CV_FILLED)

    # dilate the label with  4x4 kernel
    kernel = np.ones((4, 4), np.uint8)
    label = cv2.dilate(label, kernel, iterations=1)

    cv2.imwrite(target, label)

    if debug:
        # convert back to rgb
        label = cv2.cvtColor(label, cv2.COLOR_GRAY2RGB)
        chart = cv2.cvtColor(chart, cv2.COLOR_GRAY2RGB)

        # remove blue so that we can have colorful debug output
        label[:, :, 2] = 0

        cv2.subtract(chart, label, dst=label)
        chart = cv2.addWeighted(chart, 0.65, label, 0.35, 0)
        cv2.imwrite(debug, chart)

        # show debug output
        # cv2.imshow('image', chart)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()


if __name__ == '__main__':
    with open(sys.argv[1] + '.json') as data_file:
        data = json.load(data_file)
        gen_labeled_image(data, sys.argv[1] + '.png', 'label.png', 'debug.png')
