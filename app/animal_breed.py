import psycopg2
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

dbname = os.getenv('dbname')
user = os.getenv('user')
host = os.getenv('host')
port = os.getenv('port')
password = os.getenv('password')


while True:
    try:
        conn = psycopg2.connect(dbname=dbname, user=user,
                                password=password, host=host, port=port)
        cursor = conn.cursor()

        cursor.execute("""SELECT images.external_path, pets.id FROM images 
                          join pets_images on images.id = pets_images.image_id 
                          join pets on pets_images.pet_id = pets.id
                          where pets.breed_id = 1
                          order by pets.id
                          """)

        d = {}

        for i in cursor:
            response = requests.post("http://127.0.0.1:8000/predict/animal_type/from_url/",
                                     json={'img_path': i[0]},
                                     )



        cursor.close()
        conn.close()

    except Exception as e:
        print(e)

