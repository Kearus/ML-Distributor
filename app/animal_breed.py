# Приложение находит в БД животных без указания породы, взаимодействует с другим ML-приложением, которое сообщает породу, затем всё заносится в БД
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
link_dogs = os.getenv('link_dogs')
link_cats = os.getenv('link_cats')


breeds = {
        "scottish_deerhound": 2,
        "maltese_dog": 3,
        "afghan_hound": 4,
        "entlebucher": 5,
        "bernese_mountain_dog": 6,
        "shih-tzu": 7,
        "great_pyrenees": 8,
        "pomeranian": 9,
        "basenji": 10,
        "samoyed": 11,
        "airedale": 12,
        "tibetan_terrier": 13,
        "cairn": 14,
        "leonberg": 15,
        "beagle": 16,
        "japanese_spaniel": 17,
        "Abyssinian": 18,
        "Bengal": 19,
        "Birman": 20,
        "Bombay": 21,
        "British": 22,
        "Egyptian": 23,
        "Maine": 24,
        "Persian": 25,
        "Ragdoll": 26,
        "Russian": 27,
        "Siamese": 28,
        "Sphynx": 29
        }

# бесконечный цикл работы приложения
while True:
    try:
        # устанавливаем подключение к бд
        conn = psycopg2.connect(dbname=dbname, user=user,
                                password=password, host=host, port=port)
        cursor = conn.cursor()

        # делаем запрос к бд, собираем ссылки на фото и id по всем животным из таблицы 'pets', у которых не указана порода (значение 1 в колонке 'breed_id')
        cursor.execute("""SELECT images.external_path, pets.id, pets.animal_id FROM images 
                          join pets_images on images.id = pets_images.image_id 
                          join pets on pets_images.pet_id = pets.id
                          where pets.breed_id = 4
                          order by pets.id
                          """)

        d = {} # словарь для хранения результатов работы ML приложения. Ключ - id животного, значения в виде списка ответов ML по каждому животному

        # проходим построчно по полученному запросу к бд
        for i in cursor:
            if i[2] == 1: # если это собака, то отправляем запрос в сервис, определяющий породы собак
                response = requests.post(link_dogs,
                                         json={'img_path': i[0]},
                                        )

                # полученный результат переводим в json-формат и затем в словарь вида ключ-значение 1776: [1, 2, 1, 2, 1, 1]
                json_response = response.json()
                d[i[1]] = d.setdefault(i[1], []) + [breeds[json_response['breed']]]

            if i[2] == 2: # если это кошка, то отправляем запрос в сервис, определяющий породы кошек
                response = requests.post(link_cats,
                                         json={'img_path': i[0]},
                                        )

                # полученный результат переводим в json-формат и затем в словарь вида ключ-значение 1776: [1, 2, 1, 2, 1, 1]
                json_response = response.json()
                d[i[1]] = d.setdefault(i[1], []) + [breeds[json_response['breed']]]

#        print(d)
        cursor.close()
        conn.close()

        # проходим по словарю. Из пары ключ-значение вида 44: [14, 9, 14, 9, 14] создаём ключ-значение вида 44: 14
        for key, value in d.items():
            d[key] = max(set(value), key=value.count)

        # создаём пустой кортеж, который будет передавать значения для записи в БД
        result = tuple()

        # заносим данные в результирующий кортеж в виде ((4, 741), (7, 1843), (6, 1201))
        for key, value in d.items():
            result += (value, key),
#        print(result)

        conn = psycopg2.connect(dbname=dbname, user=user,
                                password=password, host=host, port=port)

        # обращаемся к бд и меняем в таблице 'pets' значения 1 в колонке 'breed_id' на породу животного (полученную в результате работы ML-приложения)
        # где pets.id равно второму значению каждого кортежа внутри result.
        with conn:
            cur = conn.cursor()
            query = "update pets set breed_id = %s where id = %s"
            cur.executemany(query, result)
            conn.commit()

        # закрываем соединение с бд
        cursor.close()
        conn.close()

    # если во время выполнения блока кода try происходит ошибка, выводим её, спим 1 минуту, затем повторно запускаем программу
    except Exception as e:
        print(e)

    # отправляем приложение спать на 10 минут, после чего опять повторяем его работу и ищем животных без указания породы.
    time.sleep(60 * 10)

