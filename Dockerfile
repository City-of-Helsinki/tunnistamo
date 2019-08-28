FROM python:3.6-slim

ENV PYTHONUNBUFFERED 0

RUN apt-get update \
    && apt-get install -y python-lxml libxmlsec1 libxmlsec1-dev gettext

RUN mkdir /code
WORKDIR /code

COPY . /code

RUN pip install pip==18.0 \
    && pip install -r /code/requirements.txt \
    && pip install -r /code/requirements-dev.txt \
    && pip install prequ==1.4.3
