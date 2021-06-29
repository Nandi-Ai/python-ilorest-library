FROM python:2.7.18-buster

WORKDIR /app

RUN apt-get update -y

RUN apt-get install -y vim

ADD requirements.txt requirements.txt

RUN pip2 install -r requirements.txt



