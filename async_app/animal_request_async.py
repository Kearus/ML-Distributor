''' Данное приложение делает запрос в базу данных и собирает информацию о животных без указания типа. Отправляет фото по ним в ML приложение,
 а полученный результат записывает обратно в БД.'''
import asyncio
import time
import os
from dotenv import load_dotenv
import aiohttp

from app import connect_db_async
start = time.time()
print(start)
load_dotenv()

link_types = os.getenv('link_types')

animal_type = {'dog': 1, 'cat': 2}  # словарь для дальнейшего перевода типа животного, возвращаемого приложением ML, в '1' или '2', как в указывается в бд

# бесконечная асинхронная функция по определению типа животного
async def get_animal_types():
    while True:
        try:
            # подключаемся к бд с помощью контекстного менеджера и делаем запрос на животных без указания типа.
            async with connect_db_async.conn_db() as conn:
                cursor = await conn.fetch("""SELECT images.static_path, pets.id FROM images 
                                              join pets_images on images.id = pets_images.image_id 
                                              join pets on pets_images.pet_id = pets.id
                                              where pets.animal_id = 3
                                              order by pets.id limit 300
                                              """)

            d = {}  # словарь для хранения результатов работы ML приложения. Ключ - id животного, значения в виде списка ответов ML по каждому животному
            # переводим результат запроса в бд в удобный формат списка словарей, где значения - ссылки на фото, id животного.
            data = [dict(row) for row in cursor]

            # если в списке data присутствует больше одного id - удаляем словари с последним id, т.к. в запросе бд выше стоит лимит на количество вернувшихся записей,
            # и в результате часть фото одного животного может не попасть в data. Поэтому мы возьмём этот id на следующей итерации работы функции
            if data[0]['id'] != data[-1]['id']:
                data = [i for i in data if i['id'] != data[-1]['id']]

            # проходим построчно по полученному запросу в бд
            for i in data:
                #  отправляем ссылки с фото животных в ML-приложение для определения типа животного
                try:
                    async with aiohttp.ClientSession() as client:
                        async with client.post(link_types, json={'img_path': i['static_path']},) as resp:
                            json_response = await resp.json()
                            d[i['id']] = d.setdefault(i['id'], []) + [animal_type[json_response['class_name']]]

                except Exception as ex:
                    print(ex)

            # проходим по словарю. Из пары ключ-значение вида 1776: [1, 2, 1, 2, 1, 1] создаём ключ-значение вида 1776: 1
            for key, value in d.items():
                d[key] = max(set(value), key=value.count)

            # создаём пустой кортеж, который будет передавать значения для записи в БД
            result = tuple()

            # заносим данные в результирующий кортеж в виде ((1, 1842), (1, 1843), (1, 1850))
            for key, value in d.items():
                result += (value, key),

            # обращаемся к бд и меняем в таблице 'pets' значения 3 в колонке 'animal_id' на категорию животного (полученную в результате работы ML-приложения)
            # где id.pets равно второму значению каждого кортежа внутри result.
            async with connect_db_async.conn_db() as conn:
                query = "update pets set animal_id = $1 where id = $2"
                await conn.executemany(query, result)

        # если во время выполнения блока кода try происходит ошибка, выводим её и переходим к блоку finally
        except Exception as e:
            print(e)

        # данный блок выполняется после try/except в любом случае
        finally:
            end = time.time()
            print(f'{end - start} секунд прошло для типов')
            # пытаемся повторно подключиться к бд и найти животных без указания породы.
            try:
                async with connect_db_async.conn_db() as conn:
                    cursor = await conn.fetch("""SELECT images.static_path, pets.id FROM images 
                                              join pets_images on images.id = pets_images.image_id 
                                              join pets on pets_images.pet_id = pets.id
                                              where pets.animal_id = 3
                                              order by pets.id limit 300
                                              """)
                    # если получилось найти животных без указания типа, то сразу начинаем работу функции get_animal_types() повторно
                    if len([dict(row) for row in cursor]):
                        await conn.close()
                        await get_animal_types()
                    # если нет - отправляем приложение в сон на 10 минут
                    else:
                        await asyncio.sleep(60 * 10)
            except Exception as e:
                print(e)

if __name__ == '__main__':
    get_animal_types()