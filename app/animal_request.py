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
link_types = os.getenv('link_types')

animal_type = {'dog': 1, 'cat': 2}  # словарь для дальнейшего перевода типа животного, возвращаемого приложением ML, в '1' или '2', как в указывается в бд

def get_animal_types():
# бесконечный цикл работы приложения
    while True:
        try:
            # устанавливаем подключение к бд
            conn = psycopg2.connect(dbname=dbname, user=user,
                                    password=password, host=host, port=port)
            cursor = conn.cursor()

            # делаем запрос к бд, собираем ссылки на фото и id по всем животным из таблицы 'pets', в которых в колонке 'animal_id' стоит значение Null
            cursor.execute("""SELECT images.static_path, pets.id FROM images 
                              join pets_images on images.id = pets_images.image_id 
                              join pets on pets_images.pet_id = pets.id
                              where pets.animal_id = 3
                              order by pets.id
                              """)

            d = {}  # словарь для хранения результатов работы ML приложения. Ключ - id животного, значения в виде списка ответов ML по каждому животному

            # проходим построчно по полученному запросу к бд
            for i in cursor.fetchall():
                cursor.close()

                #  отправляем ссылки с фото животных в ML-приложение для определения типа животного
                try:
                    response = requests.post(link_types,
                                         json={'img_path': i[0]},
                                         )
                # полученный результат переводим в json-формат и затем в словарь вида ключ-значение 1776: [1, 2, 1, 2, 1, 1]
                    json_response = response.json()
                    d[i[1]] = d.setdefault(i[1], []) + [animal_type[json_response['class_name']]]
                except Exception as ex:
                    print(ex)

#            print(d)

            # проходим по словарю. Из пары ключ-значение вида 1776: [1, 2, 1, 2, 1, 1] создаём ключ-значение вида 1776: 1
            for key, value in d.items():
                d[key] = max(set(value), key=value.count)

            # создаём пустой кортеж, который будет передавать значения для записи в БД
            result = tuple()

            # заносим данные в результирующий кортеж в виде ((1, 1842), (1, 1843), (1, 1850))
            for key, value in d.items():
                result += (value, key),
#            print(result)


            # обращаемся к бд и меняем в таблице 'pets' значения null в колонке 'animal_id' на категорию животного (полученную в результате работы ML-приложения)
            # где id.pets равно второму значению каждого кортежа внутри result.
            with conn:
                cur = conn.cursor()
                query = "update pets set animal_id = %s where id = %s"
                cur.executemany(query, result)
                conn.commit()

            # закрываем соединение с бд
            cursor.close()
            conn.close()

        except Exception as e:
            print(e)

        finally:
            cursor.close()
            conn.close()
            # отправляем приложение спать на 10 минут, после чего опять повторяем его работу и ищем животных без указания категории.
            time.sleep(60 * 10)

#        raise HTTPException(500, str(e))

if __name__ == '__main__':
    get_animal_types()