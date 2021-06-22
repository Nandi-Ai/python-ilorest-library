FROM python:2.7.18-buster

WORKDIR /app

RUN apt-get update -y

RUN apt-get install -y python-pip python-dev build-essential

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt



