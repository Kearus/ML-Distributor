# Приложение находит в БД животных без указания породы, взаимодействует с другим ML-приложением, которое сообщает породу, затем всё заносится в БД
import math
import asyncio
import time
import os
from dotenv import load_dotenv
import aiohttp

from app import connect_db_async
start = time.time()
print(start)
load_dotenv()

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

# функции для расчёта вероятности пород животных
async def get_init_vector(first_breed):
    res = {}
    if first_breed in breeds_dogs.values():
        for key, value in breeds_dogs.items():
            res[value] = res.setdefault(value, math.sqrt(1/len(breeds_dogs.values())))
    elif first_breed in breeds_cats.values():
        for key, value in breeds_cats.items():
            res[value] = res.setdefault(value, math.sqrt(1/len(breeds_cats.values())))
    return res

async def normalize(vector):
    sum = 0
    for xi, value in vector.items():
        sum += value*value
    return {xi: value/math.sqrt(sum) for xi, value in vector.items()}

async def get_smoothed_pb(probabilities):
    p_vector = await get_init_vector(probabilities[0][0])
    for p in probabilities:
        p_vector[p[0]] += p[1]
    p_vector = await normalize(p_vector)
    return p_vector

# бесконечная асинхронная функция по определению вероятных пород животного
async def get_breeds():
    while True:
        try:
            # подключаемся к бд с помощью контекстного менеджера и делаем запрос на животных без указания породы.
            async with connect_db_async.conn_db() as conn:
                cursor = await conn.fetch("""SELECT images.static_path, pets.id, pets.animal_id FROM images 
                                              join pets_images on images.id = pets_images.image_id 
                                              join pets on pets_images.pet_id = pets.id
                                              where pets.breed_id = 1
                                              order by pets.id limit 300
                                              """)

            d = {} # словарь для хранения результатов работы ML приложения.
            # переводим результат запроса в бд в удобный формат списка словарей, где значения - ссылки на фото, id и тип животного.
            data = [dict(row) for row in cursor]

            # если в списке data присутствует больше одного id - удаляем словари с последним id, т.к. в запросе бд выше стоит лимит на количество вернувшихся записей,
            # и в результате часть фото одного животного может не попасть в data. Поэтому мы возьмём этот id на следующей итерации работы функции
            if data[0]['id'] != data[-1]['id']:
                data = [i for i in data if i['id'] != data[-1]['id']]

            # проходим по списку, отправляем запрос в ML приложение для определения пород животных. Полученный результат переводим в json.
            for i in data:
                try:
                    if i['animal_id'] == 1: # если это собака, то отправляем запрос в сервис, определяющий породы собак
                        async with aiohttp.ClientSession() as client:
                            async with client.post(link_dogs, json={'img_path': i['static_path']}) as resp:
                                json_response = await resp.json()
                                d[i['id']] = d.setdefault(i['id'], []) + [[breeds_dogs[json_response['breed']], float(json_response['probability'])]]

                    elif i['animal_id'] == 2: # если это кошка, то отправляем запрос в сервис, определяющий породы кошек
                        async with aiohttp.ClientSession() as client:
                            async with client.post(link_cats, json={'img_path': i['static_path']}) as resp:
                                json_response = await resp.json()
                                d[i['id']] = d.setdefault(i['id'], []) + [[breeds_cats[json_response['breed']], float(json_response['probability'])]]
                except Exception as ex:
                    print(ex)

            # рассчитываем % вероятности опеределения породы, а также подготавливаем результирующие данные для последующей их записи в бд
            commiters = tuple()
            for key, value in d.items():
                data = await get_smoothed_pb(value)
                data = dict(sorted(data.items(), key=lambda item: item[1]))
                top1, prob1 = list(data.keys())[-1], list(data.values())[-1]
                top2, prob2 = list(data.keys())[-2], list(data.values())[-2]
                top3, prob3 = list(data.keys())[-3], list(data.values())[-3]
                commiters += (top1, f'{top1};{top2};{top3}', f'{round(prob1 ** 2, 3)};{round(prob2 ** 2, 3)};{round(prob3 ** 2, 3)}', key),


            # с помощью контекстного менеджера записываем результат в базу данных
            async with connect_db_async.conn_db() as conn:
                query = "update pets set breed_id = $1, top_breeds = $2, probability = $3 where id = $4"
                await conn.executemany(query, commiters)


        # если во время выполнения блока кода try происходит ошибка, выводим её и переходим к блоку finally
        except Exception as e:
            print(e)

        # данный блок выполняется после try/except в любом случае
        finally:
            end = time.time()
            print(f'{end - start} секунд прошло для пород')
            # пытаемся повторно подключиться к бд и найти животных без указания породы.
            try:
                async with connect_db_async.conn_db() as conn:
                    cursor = await conn.fetch("""SELECT images.static_path, pets.id, pets.animal_id FROM images 
                                              join pets_images on images.id = pets_images.image_id 
                                              join pets on pets_images.pet_id = pets.id
                                              where pets.breed_id = 1
                                              order by pets.id limit 300
                                              """)
                    # если получилось найти животных без породы, то сразу начинаем работу функции get_breeds() повторно
                    if len([dict(row) for row in cursor]):
                        await conn.close()
                        await get_breeds()
                    # если нет - отправляем приложение в сон на 10 минут
                    else:
                        await asyncio.sleep(60 * 10)
            except Exception as e:
                print(e)

if __name__ == '__main__':
    get_breeds()