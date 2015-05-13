import sys

import numpy as np
import cv2
from matplotlib import pyplot as plt


def analyze(image):
    img = cv2.imread(image, cv2.CV_LOAD_IMAGE_GRAYSCALE)
    # hist = cv2.calcHist([img], [0], None, [256], [0, 256])

    ret, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)

    contours, hierarchy = cv2.findContours(thresh, 1, 2)
    cnt = contours[0]

    rect = cv2.minAreaRect(cnt)
    box = cv2.cv.BoxPoints(rect)
    box = np.int0(box)
    print box
    cv2.drawContours(img, [box], 0, (0, 0, 255), 2)

    cv2.imshow('image', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # plt.hist(img.ravel(), 256, [0, 256])
    # plt.show()


if __name__ == '__main__':
    analyze(sys.argv[1])
