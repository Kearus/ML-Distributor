from threading import Thread
from animal_request import get_animal_types
from animal_breed import get_breeds

def types():
    get_animal_types()

def breeds():
    get_breeds()

Thread(target=types).start()
Thread(target=breeds).start()