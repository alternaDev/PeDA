from bottle import route, run, static_file, get, post, request
import json
import glob
import fnmatch
import os
import os.path as path
import errno

PORT = 8080

BASE_DIR = "/mnt/samba/ImageData/"
BASE_URL = "http://192.168.178.77:" + str(PORT)

@get('/getImages')
def getImagesHandler():
	from bottle import response
    	from json import dumps
	
	userValue = request.get_header('X-User')
	images = getPendingImages(userValue)
	objects = []
	for i in images:
		objects.append({'url': i.replace(BASE_DIR, BASE_URL + "/image/")})

	response.content_type = 'application/json'
	return dumps(objects)

@get('/image/<filepath:re:.*\.png>')
def getImageHandler(filepath):
	return static_file(filepath, root=BASE_DIR)

@get('/getNames')
def getNamesHandler():
	from bottle import response
	from json import dumps
	response.content_type = 'application/json'

	res = []
	if os.path.isdir(BASE_DIR + "A"):
		res = res + next(os.walk(BASE_DIR + "A"))[1]
	if os.path.isdir(BASE_DIR + "B"):
		res = res +  next(os.walk(BASE_DIR + "B"))[1]
	if os.path.isdir(BASE_DIR + "FINAL"):
		res = res + next(os.walk(BASE_DIR + "FINAL"))[1]
	return dumps(list(set(res)))

def getPendingImages(user):
	globalImages = glob.glob(BASE_DIR + '/*.png')
	aImages = rGlob(BASE_DIR + '/A/', 'png')
	bImages = rGlob(BASE_DIR + '/B/', 'png')
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
		p = ""
		if r['isPedestrian']:
			p = r['recognizedPedestrian']
		else:
			p = "___NOT_PEDESTRIAN___"
		user = request.get_header('X-User')
	
		if(os.path.isfile(BASE_DIR + "/" + filename)):
			folder = BASE_DIR + "/" + user + "/" + p
			mkdir_p(folder + "/")
			os.rename(BASE_DIR + "/" + filename, folder + "/" + filename)
			response = response +  "Moved to your folder\n"
		elif((user == "A" and os.path.isfile(BASE_DIR + "/B/" + p + "/" + filename)) or (user == "B" and os.path.isfile(BASE_DIR + "/A/" + p + "/" + filename))):
			folder = BASE_DIR + "/FINAL/" + p + "/"
			mkdir_p(folder)
			if(user == "A"):
				os.rename(findFile(filename), folder + filename)
				response = response + "Moved from Bs Folder to final\n"
			if(user == "B"):
				print(folder)
				print(filename)
				print(findFile(filename))
				os.rename(findFile(filename), folder + filename)
				response = response + "Moved from As Folder to final\n" 
		elif((user == "A" and not os.path.isfile(BASE_DIR + "/B/" + p + "/" + filename)) or (user == "B" and not os.path.isfile(BASE_DIR + "/A/" + p + "/" + filename))):
			file = findFile(filename)
			os.rename(file, BASE_DIR + "/" + filename)
			response = response + "Moved back to TODO+\n"

def findFile(filename):
	for root, dirnames, filenames in os.walk(BASE_DIR):
		matches = fnmatch.filter(filenames, filename)
		if len(matches) > 0:
			print os.path.join(root, filename)
			return os.path.join(root, filename)

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
