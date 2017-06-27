#!/usr/bin/env python

import logging
import os
import sys
import time
sys.path.append(os.path.abspath("/home/pi/PeDA"))
from detect import *

if __name__ == '__main__':

    action = sys.argv[1]
    logfile = "/mnt/samba/ImageData/peda.log"
    pidfile = os.path.join(os.getcwd(), "peda.pid")

    logging.basicConfig(filename=logfile, level=logging.DEBUG)
    d = PedestrianTracker(pidfile=pidfile)

    if action == "start":

        d.start()

    elif action == "stop":

        d.stop()

    elif action == "restart":

        d.restart()
