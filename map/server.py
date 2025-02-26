from flask import Flask, json,request
import db_connector as db
import os 
import copy
import base64
import uuid #create unique filename

app = Flask(__name__)
from mysql.connector import pooling
from mysql.connector import Error

#LoadEnv Vars
from dotenv import load_dotenv
from pathlib import Path
dotenv_path = Path('../env/.env')
load_dotenv(dotenv_path=dotenv_path)

DB_NAME = os.getenv('DB_NAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_USER = os.getenv('DB_USER')

# db_pool = db.create_pool()


@app.route("/api/map/test")
def hello2():
    return "Hello Map!"
  
@app.route('/api/map/reports')
def get_reports():
    query = '''SELECT reportId, body, DATE_FORMAT(date, '%Y-%m-%d %H:%i') date,
    type, address, cast(lat as char(11)) lat, cast(`long` as char(10)) `long`, path 
    FROM (SELECT reportId, body, date, GROUP_CONCAT(type SEPARATOR ", ") 'type'
    FROM lolo_report 
    LEFT JOIN lolo_locust_in_report USING (reportId)
    LEFT JOIN lolo_locust USING (locustId) GROUP BY reportId) as t1
    LEFT JOIN lolo_location USING (reportId)
    LEFT JOIN lolo_image_in_report USING (reportId)
    LEFT JOIN lolo_image USING (imageId)
    ORDER BY date DESC LIMIT 20;'''
    db_connection = db_pool.get_connection()
    cursor = db.execute_query(db_connection=db_connection, query=query)
    
    result={}
    if cursor!=None:
        result = json.dumps(cursor.fetchall())
    db_connection.close()
    return result


@app.errorhandler(413)
def image_too_big(e):
    ## error 413 is payload too large - probably because
    ## the images is too big
    return 'File Too Large', 413

@app.route('/api/map/submit', methods=['POST'])
def postReport():
    print("User Submitting Data")
    '''accept post request from ReportPage and input those data into the database'''
    try:
        data = request.get_json()
        cleandata=copy.deepcopy(data)
        if cleandata.get("img")!=None:
            cleandata["img"]="binarydata"
        print("User Submitted Data",cleandata,request,flush=True)
        date = data.get('date')
        position = data.get('latlng')
        lat = position.get("lat")
        lng = position.get("lng")
        
        imageName = data.get('imgName') if data.get('imgName') != '' else None
        locustType = data.get('locustType') if data.get('locustType')!= [] else None 
        reportBody = data.get('comment') if data.get('comment') != "" else None
        addr = data.get("addr") if data.get("addr") != "" else None
    
        print("latlng", position.get("lat"), position.get("lng"))
    


        if (imageName!= None):
            path = "target/assets/reportpics"
            imageName = saveImage(data.get("img").split("base64,")[1], path, imageName)
            fullpath=os.path.join(path,imageName)
            if not os.path.isfile(fullpath):
                imageName=None
            app.logger.debug(f"New image name = {imageName}")
        if (locustType!=None):
            tempString = locustType[0]
            for i in locustType[1:]:
                tempString+=","
                tempString+=i
            locustType=tempString
        ## mysql query request
        ## position and date will always be given 

    # IN dateP DATETIME,
    # IN bodyP TEXT,
    # IN addrP VARCHAR(200),
    # IN lat DECIMAL(10,8),
    # IN lng DECIMAL(11,8),
    # IN imagePathP VARCHAR(200),
    # IN locustTypeP VARCHAR(200))
        query = '''CALL addReport(%s,%s,%s,%s,%s,%s,%s);'''
        db_connection = db_pool.get_connection()
        cursor = db.execute_query(db_connection=db_connection, query=query,query_params=(date,reportBody,addr,lat, lng,imageName,locustType))

        cursor.close()
        db_connection.close()
    except Exception as e:
        print("map/server.py Error!")
        print(e)
        return {"status": "fail", "message": e}
    return {"status": "success","message": ""}
        
# Listener

def saveImage(img, path, imgName):
    # given image in string base64, save the images in that path
    # and return the name that the image is saved under
    newImageName = str(uuid.uuid4()) # create a unique name 
    extension = imgName.split(".")[1]
    image = open(f"{path}/{newImageName}.{extension}", "wb")

    # The image sent from the frontend is in string (because we jsonified it)
    # the actual image is in base64 in string format, so must write the image this way
    image.write(base64.b64decode(img))
    image.close()
    return newImageName+"."+extension

if __name__ == "__main__":
    db_pool = db.create_pool()
    app.run(host='0.0.0.0', debug=True) 