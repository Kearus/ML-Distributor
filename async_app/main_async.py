# Данный модуль запускает асинхронное многопоточное выполнение приложений по определению типа животного и породы.
from threading import Thread
from animal_request_async import get_animal_types
from animal_breed_async import get_breeds
import asyncio

async def main():
    task1 = main_loop.create_task(get_animal_types())
    task2 = main_loop.create_task(get_breeds())
    await asyncio.gather(task1, task2)
    Thread(target=get_animal_types).start()
    Thread(target=get_breeds).start()

main_loop = asyncio.get_event_loop()
main_loop.run_until_complete(main())
main_loop.run_forever()
