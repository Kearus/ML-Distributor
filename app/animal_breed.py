# Приложение находит в БД животных без указания породы, взаимодействует с другим ML-приложением, которое сообщает породу, затем всё заносится в БД
import math
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

breeds_dogs = {
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
        "japanese_spaniel": 17, # 0.0625(1/16)
}
breeds_cats = {
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
        "Sphynx": 29 # 0.0833(1/12)
}

def get_init_vector(first_breed):
    res = {}
    if first_breed in breeds_dogs.values():
        for key, value in breeds_dogs.items():
            res[value] = res.setdefault(value, math.sqrt(1/len(breeds_dogs.values())))
    elif first_breed in breeds_cats.values():
        for key, value in breeds_cats.items():
            res[value] = res.setdefault(value, math.sqrt(1/len(breeds_cats.values())))
    return res

def normalize(vector):
    sum = 0
    for xi, value in vector.items():
        sum += value*value
    return {xi: value/math.sqrt(sum) for xi, value in vector.items()}

def get_smoothed_pb(probabilities):
    p_vector = get_init_vector(probabilities[0][0])
    for p in probabilities:
        p_vector[p[0]] += p[1]
    p_vector = normalize(p_vector)
    return p_vector
            
def get_breeds():
# бесконечный цикл работы приложения
    while True:
        try:
            # устанавливаем подключение к бд
            conn = psycopg2.connect(dbname=dbname, user=user,
                                    password=password, host=host, port=port)
            cursor = conn.cursor()

            # делаем запрос к бд, собираем ссылки на фото и id по всем животным из таблицы 'pets', у которых не указана порода (значение 1 в колонке 'breed_id')
            cursor.execute("""SELECT images.static_path, pets.id, pets.animal_id FROM images 
                              join pets_images on images.id = pets_images.image_id 
                              join pets on pets_images.pet_id = pets.id
                              where pets.breed_id = 1
                              order by pets.id
                              """)

            d = {} # словарь для хранения результатов работы ML приложения. Ключ - id животного, значения в виде списка ответов ML по каждому животному

            # проходим построчно по полученному запросу к бд
            for i in cursor.fetchall():
                cursor.close()
                try:
                    if i[2] == 1: # если это собака, то отправляем запрос в сервис, определяющий породы собак
                        response = requests.post(link_dogs, json={'img_path': i[0]})
                        json_response = response.json()
                        d[i[1]] = d.setdefault(i[1], []) + [[breeds_dogs[json_response['breed']], float(json_response['probability'])]]

                    elif i[2] == 2: # если это кошка, то отправляем запрос в сервис, определяющий породы кошек
                        response = requests.post(link_cats, json={'img_path': i[0]})
                        json_response = response.json()
                        d[i[1]] = d.setdefault(i[1], []) + [[breeds_cats[json_response['breed']], float(json_response['probability'])]]
                except Exception as ex:
                    print(ex)

#            print(d)
            commiters = tuple()
            for key, value in d.items():
                data = get_smoothed_pb(value)
    #            print(data)
                data = dict(sorted(data.items(), key=lambda item: item[1]))
    #            print(data)
                top1, prob1 = list(data.keys())[-1], list(data.values())[-1]
                top2, prob2 = list(data.keys())[-2], list(data.values())[-2]
                top3, prob3 = list(data.keys())[-3], list(data.values())[-3]
                commiters += (top1, f'{top1};{top2};{top3}', f'{round(prob1 ** 2, 3)};{round(prob2 ** 2, 3)};{round(prob3 ** 2, 3)}', key),
    #            print((top1, f'{top1};{top2};{top3}', f'{round(prob1 ** 2, 3)};{round(prob2 ** 2, 3)};{round(prob3 ** 2, 3)}', key))


#            print(commiters)


            # обращаемся к бд и меняем в таблице 'pets' значения 1 в колонке 'breed_id' на породу животного (полученную в результате работы ML-приложения)
            # где pets.id равно второму значению каждого кортежа внутри result.
            with conn:
                cur = conn.cursor()
                query = "update pets set breed_id = %s, top_breeds = %s, probability = %s where id = %s"
                cur.executemany(query, commiters)
                conn.commit()

            # закрываем соединение с бд
            cursor.close()
            conn.close()

        # если во время выполнения блока кода try происходит ошибка, выводим её, спим 1 минуту, затем повторно запускаем программу
        except Exception as e:
            print(e)

        finally:
            cursor.close()
            conn.close()
            # отправляем приложение спать на 10 минут, после чего опять повторяем его работу и ищем животных без указания породы.
            time.sleep(60 * 10)


if __name__ == '__main__':
    get_breeds()