FROM python:3.9

COPY /app/ /app/

COPY ./req.txt /app/req.txt

WORKDIR /app/

RUN pip install -r req.txt

CMD ["python", "./main.py"]

