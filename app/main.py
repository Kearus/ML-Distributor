from threading import Thread

def types():
    while True:
        exec(open("animal_request.py", encoding='UTF-8').read())

def breeds():
    while True:
        exec(open("animal_breed.py", encoding='UTF-8').read())

Thread(target=types).start()
Thread(target=breeds).start()