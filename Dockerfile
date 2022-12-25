FROM python:3.11.1-slim

WORKDIR /nibe-exporter

COPY nibe-exporter.py requirements.txt /nibe-exporter/

RUN set -xe && \
    pip install -r requirements.txt

ENTRYPOINT . /nibe-exporter/.env && /nibe-exporter/nibe-exporter.py
