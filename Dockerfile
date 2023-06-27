# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster
RUN apt-get update && apt-get install -y zip
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
CMD ["python", "server.py"]