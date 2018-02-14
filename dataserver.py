from bottle import route, run, template, response, static_file
import psycopg2
from json import dumps
import json
try:
    conn = psycopg2.connect("dbname='postgres' user='postgres' host='localhost' password='raspberry'")
except:
    print "I am unable to connect to the database"

STATIC_BASE_URL = "http://192.168.178.75:8080/image"

class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super(DatetimeEncoder, obj).default(obj)
        except TypeError:
            return obj.strftime('%Y-%m-%dT%H:%M:%S')

@route('/names')
def names():
	cur = conn.cursor()
	cur.execute("SELECT DISTINCT name from images;")
	r = cur.fetchall()
	res = []
	for n in r:
		res.append(n[0])
	cur.close()
	response.content_type = "application/json"
	return dumps(res)

@route('/data/<name>')
def data(name):
	cur = conn.cursor()
	cur.execute("""WITH x AS
(
    SELECT
    filename, path, name, status, time,
    ROW_NUMBER() OVER
        (PARTITION BY status, name ORDER BY time DESC) AS RN
    FROM images
      WHERE time NOTNULL AND name = %s

)
select * from x
WHERE NOT EXISTS
(
  SELECT 1 FROM x AS x2
  WHERE x2.name = x.name
  AND x2.status = x.status
  AND x2.rn = x.rn + 1
  AND abs(extract(second from x2.time - x.time)) < 15
)
ORDER BY x.time;""", (name,))
	r = cur.fetchall()
        res = []
        for n in r:
                res.append({"id": n[0], "path": n[1].replace("/mnt/samba/ImageData", STATIC_BASE_URL), "name": n[2], "status": n[3], "time": n[4]})
        cur.close()
        response.content_type = "application/json"
        return dumps(res, cls=DatetimeEncoder)

@route('/<path:path>')
def callback(path):
    return static_file(path, "./static")	

@route('/')
def c():
	return static_file("index.html", "./static")

run(host='0.0.0.0', port=8081)
