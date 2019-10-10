FROM python:3.6-slim

RUN apt-get update && \
    apt-get install -y \
      gcc \
      vim-tiny && \
    pip install --upgrade pip

COPY . /code
WORKDIR /code
RUN  pip install -r requirements.txt

ENV FLASK_APP=/code/app.py
EXPOSE 5000

CMD uwsgi --module app:app \
    --http-socket 0.0.0.0:5000 --master \
    --processes 2 --threads 2 \
    --stats /tmp/stats.socket \
    --wsgi-disable-file-wrapper
