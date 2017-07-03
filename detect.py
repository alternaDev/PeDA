#!/usr/bin/env python
# import the necessary packages
from __future__ import print_function
from imutils.object_detection import non_max_suppression
from imutils import paths
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
from skimage.measure import compare_ssim as ssim
import numpy as np
import tensorflow as tf

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

modelFullPath = './pedestrian_graph.pb'
labelsFullPath = './pedestrian_labels.txt'


def create_graph():
    """Creates a graph from saved GraphDef file and returns a saver."""
    # Creates graph from saved graph_def.pb.
    with tf.gfile.FastGFile(modelFullPath, 'rb') as f:
        graph_def = tf.GraphDef()
        graph_def.ParseFromString(f.read())
        _ = tf.import_graph_def(graph_def, name='')

def diff_img(t0, t1, t2):
    d1 = cv2.absdiff(t2, t1)
    d2 = cv2.absdiff(t1, t0)
    return cv2.bitwise_and(d1, d2)

def something_has_moved(imageA, imageB, threshold=0.01):
    nZ = 1 - ssim(imageA, imageB)
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

    image = cam.read()[1]
    t = imutils.resize(cv2.cvtColor(image, cv2.COLOR_RGB2GRAY), width=min(200, image.shape[1]))
    image = cam.read()[1]
    t_plus = imutils.resize(cv2.cvtColor(image, cv2.COLOR_RGB2GRAY), width=min(200, image.shape[1]))

    while True:
        ret_val, image = cam.read()
        if ret_val:
            t = t_plus
            t_plus = imutils.resize(cv2.cvtColor(image, cv2.COLOR_RGB2GRAY), width=min(200, image.shape[1]))
            if something_has_moved(cv2.GaussianBlur(t, (11,11), 0), cv2.GaussianBlur(t_plus, (11,11), 0)):
                n, diff = ssim(t, t_plus, full=True)

                queue.put((image, diff, datetime.now(),))
                print("Queue Size: %d" % queue.qsize())
            #cv2.imwrite(targetFolder + "/current.jpg", diff)
        time.sleep(0.03)


def image_analyzer(queue, targetFolder):
    logging.info("Starting Analyzer")

    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    create_graph()

    f = open(labelsFullPath, 'rb')
    lines = f.readlines()
    labels = [str(w).replace("\n", "") for w in lines]

    with tf.Session() as sess:
        while True:
            time.sleep(0.2)
            image_date = queue.get()
            image = image_date[0]
            diff = image_date[1]
            date = image_date[2]

            orig = image.copy()
            image = imutils.resize(image, width=min(450, image.shape[1]))
        #cv2.imwrite(targetFolder + "/test.jpg", image)
            # Determine Scale
            origHeight, origWidth = orig.shape[:2]
            height, width = image.shape[:2]
            scaleW = origWidth  * 1.0 / width
            scaleH = origHeight * 1.0 / height

            (rects, weights) = hog.detectMultiScale(image, winStride=(4, 4),
                        padding=(8, 8), scale=1.03)

            rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
            pick = non_max_suppression(rects, probs=None, overlapThresh=0.85)

            i = 0
            for (xA, yA, xB, yB) in pick:
                logging.info("Found someone!")
                print("Found someone!")
                name = date.strftime("%Y_%m_%d__%H_%M_%S_%f_") + str(i)
                cv2.imwrite(targetFolder + "/" + name + '.jpg', orig[int(math.floor(yA * scaleH)) : int(math.ceil(yB * scaleH)), int(math.floor(xA * scaleW)) : int(math.ceil(xB * scaleW))])
                i = i + 1
            if len(pick) > 0:
                cv2.imwrite(targetFolder + "/FULL/" + name + '.jpg', orig)

            if len(pick) == 0:
                diff = (diff * 255).astype("uint8")
                thresh = cv2.threshold(diff, 0, 255,
    	           cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
                # let's use the diff.
                d, contours, hier = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE)
                if len(contours) == 0:
                    print("Nothing found. saving full image")
                    name = date.strftime("%Y_%m_%d__%H_%M_%S_%f")
                    cv2.imwrite(targetFolder + "/OnlyMove/" + name + '.jpg', orig)
                else:
                    print("Found contours. Using them.")
                    height, width = diff.shape[:2]
                    scaleW = origWidth  * 1.0 / width
                    scaleH = origHeight * 1.0 / height
                    i = 0
                    name = date.strftime("%Y_%m_%d__%H_%M_%S_%f_") + str(i)
                    write = False
                    for c in contours:
                        xA, yA, w, h = cv2.boundingRect(c)
                        xB = xA + w
                        yB = yA + h
                        origWidth = w * scaleW
                        origHeight = h * scaleH
                        if (origWidth >= 100 and origHeight >= 100):
                            write = True
                            file_name = targetFolder + "/" + name + '.jpg'
                            cv2.imwrite(file_name, orig[int(math.floor(yA * scaleH)) : int(math.ceil(yB * scaleH)), int(math.floor(xA * scaleW)) : int(math.ceil(xB * scaleW))])
                            if is_not_pedestrian(file_name, labels, sess):
                                # delete image
                                print("No pedestrian!")
                    if write:
                        cv2.imwrite(targetFolder + "/FULL/" + name + '.jpg', orig)
                    i = i + 1
    #    orig.release()
    #    image.release()

def is_not_pedestrian(image_path, labels, sess):
    image_data = tf.gfile.FastGFile(imagePath, 'rb').read()

    softmax_tensor = sess.graph.get_tensor_by_name('final_result:0')
    predictions = sess.run(softmax_tensor,
                           {'DecodeJpeg/contents:0': image_data})
    predictions = np.squeeze(predictions)

    top_k = predictions.argsort()[-5:][::-1]  # Getting top 5 predictions

    for node_id in top_k:
        human_string = labels[node_id]
        score = predictions[node_id]
        print('%s (score = %.5f)' % (human_string, score))

    answer = labels[top_k[0]]
    # is not pedestrian if the confidence of that is over 0.95
    return answer == "not pedestrian" and predictions[top_k[0]] >= 0.95

if __name__=='__main__':
    logger.info("Starting Main")
    queue = Queue()

    num_consumers = multiprocessing.cpu_count() - 1
    logger.info('Creating %d consumers' % num_consumers)
    consumers = [ Process(target=image_analyzer, args=(queue,targetFolder,))
                  for i in xrange(num_consumers) ]
    for w in consumers:
        w.start()

    image_taker(queue)


cam.release()
