import json
import os
import math

import numpy as np
import cv2

WHITE = (255, 255, 255)
RED = (0, 0, 255)
factor = 1


def gen_labeled_image(description):
    bounds = np.array(description['ImageBB'])

    bounds *= factor

    x0 = bounds[0]
    y0 = bounds[1]
    # w = bounds[2] - x0
    # h = bounds[3] - y0

    chart = cv2.imread('test.png', cv2.IMREAD_COLOR)
    h, w, _ = chart.shape

    print "Image bounds: {} x {}".format(w, h)

    label = np.zeros((h, w, 3), np.uint8)

    for text_box in description['ImageText']:
        tb = np.array(text_box['TextBB'])
        tb *= factor

        tx0 = int(math.floor(tb[0] - x0))
        ty0 = int(math.floor(tb[1] - y0))
        tx1 = int(math.ceil(tb[2] - x0))
        ty1 = int(math.ceil(tb[3] - y0))

        cv2.rectangle(label, (tx0, ty0), (tx1, ty1), WHITE, cv2.cv.CV_FILLED)

    cv2.imwrite(os.path.abspath('label.png'), label)

    label[:, :, 2] = 0

    cv2.subtract(chart, label, dst=label)
    chart = cv2.addWeighted(chart, 0.65, label, 0.35, 0)
    cv2.imwrite('debug.png', chart)


if __name__ == '__main__':
    with open('test.json') as data_file:
        data = json.load(data_file)
        gen_labeled_image(data)
