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

class PedestrianTracker(run.RunDaemon): 
  def run(self):
    targetFolder = '/mnt/samba/ImageData'
  
    cam = cv2.VideoCapture(0)
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    
    while True:
      # initialize the HOG descriptor/person detector
      #print(time.strftime("%Y_%m_%d__%H_%M_%S_") + "Loop iteration.")
      # loop over the image paths
      ret_val, image = cam.read()
      # load the image and resize it to (1) reduce detection time
      # and (2) improve detection accuracy
      orig = image.copy()
      image = imutils.resize(image, width=min(300, image.shape[1]))
      origHeight, origWidth = orig.shape[:2]
      height, width = image.shape[:2]
      # detect people in the image
      (rects, weights) = hog.detectMultiScale(image, winStride=(4, 4),
     	padding=(8, 8), scale=1.05)
    
      # apply non-maxima suppression to the bounding boxes using a
      # fairly large overlap threshold to try to maintain overlapping
      # boxes that are still people
      rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
      pick = non_max_suppression(rects, probs=None, overlapThresh=0.65)
    
      i = 0
      # draw the final bounding boxes
      for (xA, yA, xB, yB) in pick:
        print("lel")
        w = int(round(origWidth / width))
        h = int(round(origHeight / height))
        name = time.strftime("%Y_%m_%d__%H_%M_%S_") + str(i)
        cv2.imwrite(targetFolder + "/" + name + '.png', orig[yA * h : yB * h, xA * w :xB * w])
        i = i + 1
    
      time.sleep(0.01)
    cam.release()


