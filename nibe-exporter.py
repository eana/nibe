#!/usr/bin/env python
# coding: utf-8

import logging
import re
import time
from os import environ

import requests
from bs4 import BeautifulSoup
from prometheus_client import Gauge, start_http_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class CustomExporter:

    def __init__(self, url: str, username: str, password: str) -> None:
        self.url = url
        self.username = username
        self.password = password
        self.metric_dict = {}

        self.s = requests.Session()

    def login(self) -> None:

        payload = {
            "Email": self.username,
            "Password": self.password,
        }

        logging.info(f"Logging in to {url}")
        self.s.post(url + "/LogIn", data=payload)

        res = self.s.get(url)

        if res.content.decode("utf-8").find('Log out') == -1:
            logging.info(f"Failed to log in to {url}")
            exit(1)
        else:
            logging.info(f"Logged in to {url}")

    def get_data(self) -> str:
        logging.info("Fetch the data")

        res = self.s.get(self.url + "/System/169626/Status/ServiceInfo")

        # the content of the page
        return res.content.decode("utf-8")

    def replace_chars(self, metric_name) -> str:
        for ch in [" ", "-"]:
            if ch in metric_name:
                metric_name = (metric_name.replace(ch, "_").replace(
                    ".", "").replace(",", ""))

        return metric_name

    def create_metrics(self):
        logging.info("Create the metrics")

        match = r"^[-+]?\d+[,.]?\d*"

        soup = BeautifulSoup(self.get_data(), features="html.parser")

        for span in soup.find_all("span"):
            span.unwrap()

        tables = soup.find_all("table")[:6]
        for table in tables:
            rows = table.find_all("tr")[1:]
            for row in rows:
                values = [x.text.strip() for x in row.find_all("td")]

                metric_name = self.replace_chars(values[0])

                if len(re.findall(match, values[1])):
                    value = float(re.findall(match, values[1])[0])
                else:
                    value = None

                if self.metric_dict.get(metric_name) is None:
                    self.metric_dict[metric_name] = Gauge(metric_name, "")

                if type(value) == int or type(value) == float:
                    self.metric_dict[metric_name].set(value)

    def main(self):
        frequency = 15
        exporter_port = int(environ.get("EXPORTER_PORT", "9877"))
        start_http_server(exporter_port)
        logging.info(f"Listening on {exporter_port}")

        self.login()

        while True:
            self.create_metrics()
            logging.info(f"Wait for {frequency} seconds")
            time.sleep(frequency)


if __name__ == "__main__":
    url = "https://www.nibeuplink.com"

    if ("NIBE_USERNAME" not in environ) or ("NIBE_PASSWORD" not in environ):
        print('You need to define the NIBE_USERNAME and NIBE_PASSWORD '
              'environment variables.')
        exit(1)

    username = environ['NIBE_USERNAME']
    password = environ['NIBE_PASSWORD']

    c = CustomExporter(url, username, password)
    c.main()
