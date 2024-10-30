# syntax=docker/dockerfile:1
FROM python:3.10-alpine

WORKDIR /app/fileprocessor

COPY requirements.txt requirements.txt
RUN apk add --no-cache gcc musl-dev linux-headers && \
    apt-get install tesseract-ocr -y && \
    apt install tesseract-ocr-heb -y && \
    apt-get install poppler-utils -y && \
    pip install -r requirements.txt

COPY . .

ENTRYPOINT [ "./entrypoint.sh" ]