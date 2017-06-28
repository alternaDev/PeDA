#!/usr/bin/env python
# import the necessary packages
from __future__ import print_function
from imutils.object_detection import non_max_suppression
from imutils import paths
from daemons.prefab import run
import numpy as np
import sys
import imutils
import cv2
import time
import argparse
from datetime import datetime
import os
import logging
import logging.handlers
import sys

LOG_FILENAME = "/tmp/peda.log"
LOG_LEVEL = logging.INFO

parser = argparse.ArgumentParser(description='Process some things.')
parser.add_argument('--target',
                    help='Target folder')
parser.add_argument("-l", "--log", help="file to write log to (default '" + LOG_FILENAME + "')")
args = parser.parse_args()

targetFolder = args.target

if args.log:
        LOG_FILENAME = args.log

# Configure logging to log to a file, making a new file at midnight and keeping the last 3 day's data
# Give the logger a unique name (good practice)
logger = logging.getLogger(__name__)
# Set the log level to LOG_LEVEL
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)

# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
        def __init__(self, logger, level):
                """Needs a logger and a logger level."""
                self.logger = logger
                self.level = level

        def write(self, message):
                # Only log if there is a message (not just a new line)
                if message.rstrip() != "":
                        self.logger.log(self.level, message.rstrip())

# Replace stdout with logging to file at INFO level
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)
  
cam = cv2.VideoCapture(0)
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

# pre calculatue scale factor
ret_val, image = cam.read()
orig = image.copy()
image = imutils.resize(image, width=min(400, image.shape[1]))
origHeight, origWidth = orig.shape[:2]
height, width = image.shape[:2]
scaleW = int(round(origWidth / width))
scaleH = int(round(origHeight / height))

logger.info("Starting Analysis")

while True:
  a = datetime.now()
  # initialize the HOG descriptor/person detector
  #print(time.strftime("%Y_%m_%d__%H_%M_%S_") + "Loop iteration.")
  # loop over the image paths
  ret_val, image = cam.read()
  # load the image and resize it to (1) reduce detection time
  # and (2) improve detection accuracy
  orig = image.copy()
  image = imutils.resize(image, width=min(300, image.shape[1]))

  # detect people in the image
  (rects, weights) = hog.detectMultiScale(image, winStride=(4, 4),
  padding=(8, 8), scale=1.15)

  # apply non-maxima suppression to the bounding boxes using a
  # fairly large overlap threshold to try to maintain overlapping
  # boxes that are still people
  rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
  pick = non_max_suppression(rects, probs=None, overlapThresh=0.65)

  i = 0
  # draw the final bounding boxes
  for (xA, yA, xB, yB) in pick:
    logging.info("Found someone!")
        
    name = time.strftime("%Y_%m_%d__%H_%M_%S_") + str(i)

    cv2.imwrite(targetFolder + "/" + name + '.png', orig[yA * scaleH : yB * scaleH, xA * scaleW : xB * scaleW])
    i = i+ 1
#      print("Processing took " + str((datetime.now() - a).total_seconds()) + "s")
  time.sleep(0.01)

cam.release()
