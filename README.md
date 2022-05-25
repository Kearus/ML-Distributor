# Приложение для подкачки изображений с сайтов приютов

Написано на Python с использованием библиотеки: FastAPI

## Для запуска в контейнере
```
docker-compose up --build -d
```

## Для запуска локально

Создайте и запустите виртуальное окружение
```
(windows)
python -m venv venv
.\venv\Script\sctivate

(linux/macOS)
python3 -m venv venv
source venv/bin/activate
```
Установите зависимости
```
pip install -r req.txt
```
Запустите приложение
```
uvicorn main:app --host 0.0.0.0 --port 8585
```