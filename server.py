#-*- coding: utf-8 -*-

from bottle import route, run, static_file, get, post, request, BaseRequest
import json
import glob
import fnmatch
import os
import os.path as path
import errno
import shutil
import psycopg2
from datetime import datetime
import sys  

reload(sys)  
sys.setdefaultencoding('utf8')

try:
    conn = psycopg2.connect("dbname='postgres' user='postgres' host='localhost' password='raspberry'")
except:
    print "I am unable to connect to the database"

BaseRequest.MEMFILE_MAX = 1024 * 1024

PORT = 8080

BASE_DIR = u"/mnt/samba/ImageData/"
BASE_URL = u"http://192.168.178.75:" + str(PORT)

@get('/getImages')
def getImagesHandler():
	from bottle import response
    	from json import dumps

	userValue = request.get_header('X-User')
	images = getPendingImages(userValue)
	objects = []
	for i in images:
		fName = i.replace(BASE_DIR, BASE_URL + u"/image/")
		otherSuggestion = path.dirname(fName).split("/")[-2]
		if otherSuggestion == "192.168.178.75:8080":
			otherSuggestion = None
		objects.append({'url': i.replace(BASE_DIR, BASE_URL + "/image/"), 'otherSuggestion': otherSuggestion})

	response.content_type = 'application/json'
	return dumps(objects)

@get('/image/<filepath:re:.*\.jpg>')
def getImageHandler(filepath):
	return static_file(filepath.encode("utf-8"), root=BASE_DIR)

@get('/getNames')
def getNamesHandler():
	from bottle import response
	from json import dumps
	response.content_type = 'application/json'

	res = []
	if os.path.isdir(BASE_DIR + "A"):
		res = res + next(os.walk(BASE_DIR + u"A"))[1]
	if os.path.isdir(BASE_DIR + "B"):
		res = res +  next(os.walk(BASE_DIR + u"B"))[1]
	if os.path.isdir(BASE_DIR + "FINAL"):
		res = res + next(os.walk(BASE_DIR + u"FINAL"))[1]

	return dumps(list(set(filter(lambda x: x != u"___NOT_PEDESTRIAN___", res))))

def getPendingImages(user):
	globalImages = glob.glob(BASE_DIR + '/*.jpg')
	aImages = rGlob(BASE_DIR + 'A/', 'jpg')
	bImages = rGlob(BASE_DIR + 'B/', 'jpg')
	if user == 'A':
		return globalImages + bImages
	return globalImages + aImages

@post('/results')
def postResultsHandler():
	res = request.json
	response = ""
	for r in res:
		print r
		filename = r['fileName']
		p = u""
		if r['isPedestrian']:
			p = r['recognizedPedestrian'] + u"/" + r['status']
		else:
			p = "___NOT_PEDESTRIAN___"
		user = request.get_header('X-User').decode('utf8')

		if(os.path.isfile(BASE_DIR + u"/" + filename)):
			folder = BASE_DIR + u"/" + user + u"/" + p
			mkdir_p(folder + u"/")
			move(filename, BASE_DIR + u"/" + filename, folder + u"/" + filename)
			response = response +  u"Moved to your folder\n"
		elif((user == "A" and os.path.isfile(BASE_DIR + "/B/" + p + u"/" + filename)) or (user == "B" and os.path.isfile(BASE_DIR + u"/A/" + p + u"/" + filename))):
			folder = BASE_DIR + u"/FINAL/" + p + u"/"
			mkdir_p(folder)
			if(user == "A"):
				move(filename, findFile(filename), folder + filename)
				response = response + "Moved from Bs Folder to final\n"
			if(user == "B"):
				move(filename, findFile(filename), folder + filename)
				response = response + "Moved from As Folder to final\n"
			try:
				d = datetime.strptime(filename[:27], "%Y_%m_%d__%H_%M_%S_%f")
			except:
				d = datetime.strptime(filename[:20], "%Y_%m_%d__%H_%M_%S")
			if p != "___NOT_PEDESTRIAN___":
				addInfo(filename, r['recognizedPedestrian'], d, r['status'], folder + filename)

		elif((user == "A" and not os.path.isfile(BASE_DIR + u"/B/" + p + u"/" + filename)) or (user == "B" and not os.path.isfile(BASE_DIR + u"/A/" + p + u"/" + filename))):
			file = findFile(filename)
			folder = BASE_DIR + u"/" + user + u"/" + p
			mkdir_p(folder + u"/")
			move(filename, file, folder + u"/" + filename)
			response = response + "Moved as TODO into your folder\n"
	
	print(response)
	return response

def findFile(filename):
	dbRes = findFileDB(filename)
	if dbRes and os.path.isfile(dbRes):
		return dbRes
	for root, dirnames, filenames in os.walk(BASE_DIR):
		matches = fnmatch.filter(filenames, filename)
		if len(matches) > 0:
			path = os.path.join(root, filename)
			cur = conn.cursor()
		        try:
                		cur.execute("UPDATE images SET path=%s WHERE filename = %s;", (path, filename))
        		except psycopg2.Error as e:
                		print "sql error update"
        		try:
                		cur.execute("INSERT INTO images(filename, path) VALUES(%s, %s)", (filename, path))
        		except:
                		print "sql error insert"

        		conn.commit()
        		cur.close()

			return path

def findFileDB(filename):
	cur = conn.cursor()
	try:
		cur.execute("SELECT path from images WHERE filename = %s", (filename,))
	except psycopg2.Error as e:
		print e.pgerror
        	print e.diag.message_detail
		print "I can't SELECT from path"
	try:
		o = cur.fetchone()
		if o:
			conn.commit()
			cur.close()
			return o[0]
	except:
		print "ulf"
	return None

def move(filename, fromP, toP):
	shutil.move(fromP, toP)
	cur = conn.cursor()
	try:
		cur.execute("UPDATE images SET path=%s WHERE filename = %s;", (toP, filename))
		
	except psycopg2.Error as e:
		print "sql error update"
	
	conn.commit()
	cur.close()
	
	cur = conn.cursor()
	try:

		cur.execute("INSERT INTO images(filename, path) VALUES(%s, %s)", (filename, toP))
	except:
		print "sql error insert"

	conn.commit()
	cur.close()

def addInfo(filename, name, time, status, path):
	cur = conn.cursor()
	try:
		cur.execute("UPDATE images SET name=%s, time=%s, status=%s, path=%s WHERE filename = %s;", (name, time, status, path, filename))
	except psycopg2.Error as e:
		print e
	conn.commit()
	cur.close()
	
def rGlob(folder, ending):
	matches = []
	for root, dirnames, filenames in os.walk(folder):
		for filename in fnmatch.filter(filenames, '*.' + ending):
			matches.append(os.path.join(root, filename))
	return matches

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


run(host='0.0.0.0', port=8080)
