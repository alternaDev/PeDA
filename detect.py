#!/usr/bin/env python
# import the necessary packages
from __future__ import print_function
from imutils.object_detection import non_max_suppression
from imutils import paths
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
import math
import atexit
from multiprocessing import Process, Queue
import multiprocessing

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
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
if not args.log:
	logger.addHandler(ch)
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

if args.log:
	# Replace stdout with logging to file at INFO level
	sys.stdout = MyLogger(logger, logging.INFO)
	# Replace stderr with logging to file at ERROR level
	sys.stderr = MyLogger(logger, logging.ERROR)


def diff_img(t0, t1, t2):
	d1 = cv2.absdiff(t2, t1)
	d2 = cv2.absdiff(t1, t0)
	return cv2.bitwise_and(d1, d2)

def something_has_moved(image, width, height, threshold=1.15):
	nZ = cv2.mean(image)[0]

	if nZ > threshold: #If over the ceiling trigger the alarm
		print(str(nZ) + " " + str(threshold))
		return True
	else:
		return False

def image_taker(queue):
	logging.info("Starting picture taker")
	cam = cv2.VideoCapture(0)

	@atexit.register
	def goodbye():
		logger.info("Peace out!")
		cam.release()

	cam.set(3, 1280)
	cam.set(4, 720)
	time.sleep(2)

	t_minus = cv2.cvtColor(cam.read()[1], cv2.COLOR_RGB2GRAY)
	t = cv2.cvtColor(cam.read()[1], cv2.COLOR_RGB2GRAY)
	t_plus = cv2.cvtColor(cam.read()[1], cv2.COLOR_RGB2GRAY)

	while True:
		ret_val, image = cam.read()
		if ret_val:
			t_minus = t
			t = t_plus
			t_plus = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
			height, width = image.shape[:2]
			diff = diff_img(t_minus, t, t_plus)
			if something_has_moved(diff, width, height):
				queue.put((image, datetime.now(),))
				print("Queue Size: %d" % queue.qsize())
			#cv2.imwrite(targetFolder + "/current.jpg", diff)
		time.sleep(0.1)


def image_analyzer(queue, targetFolder):
	logging.info("Starting Analyzer")

	hog = cv2.HOGDescriptor()
	hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
	while True:
		time.sleep(0.2)
		image_date = queue.get()
		image = image_date[0]
		date = image_date[1]

		orig = image.copy()
		image = imutils.resize(image, width=min(500, image.shape[1]))
	#cv2.imwrite(targetFolder + "/test.jpg", image)
		# Determine Scale
		origHeight, origWidth = orig.shape[:2]
		height, width = image.shape[:2]
		scaleW = origWidth  * 1.0 / width
		scaleH = origHeight * 1.0 / height

		(rects, weights) = hog.detectMultiScale(image, winStride=(4, 4),
					padding=(8, 8), scale=1.05)

		rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
		pick = non_max_suppression(rects, probs=None, overlapThresh=0.85)

		i = 0
		for (xA, yA, xB, yB) in pick:
			logging.info("Found someone!")
			print("Found someone!")
			name = date.strftime("%Y_%m_%d__%H_%M_%S_%f_") + str(i)
			cv2.imwrite(targetFolder + "/" + name + '.jpg', orig[int(math.floor(yA * scaleH)) : int(math.ceil(yB * scaleH)), int(math.floor(xA * scaleW)) : int(math.ceil(xB * scaleW))])
			cv2.imwrite(targetFolder + "/FULL/" + name + '.jpg', orig)
			i = i + 1
		if len(pick) == 0:
			name = date.strftime("%Y_%m_%d__%H_%M_%S_%f")
			cv2.imwrite(targetFolder + "/OnlyMove/" + name + '.jpg', orig)
#	orig.release()
#	image.release()

if __name__=='__main__':
	logger.info("Starting Main")
	queue = Queue()

	num_consumers = multiprocessing.cpu_count() -2
	logger.info('Creating %d consumers' % num_consumers)
	consumers = [ Process(target=image_analyzer, args=(queue,targetFolder,))
				  for i in xrange(num_consumers) ]
	for w in consumers:
		w.start()

	image_taker(queue)


cam.release()
