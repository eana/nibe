#!/usr/bin/env python
# coding: utf-8

import logging
import re
import time
from os import environ

import requests
from bs4 import BeautifulSoup
from prometheus_client import Gauge, start_http_server

logging.basicConfig(level=logging.WARNING, format="%(message)s")


class CustomExporter:

    def __init__(self, url: str, username: str, password: str) -> None:
        self.url = url
        self.username = username
        self.password = password
        self.metric_dict = {}
        self.logged_in = False
        self.last_login_check_time = 0
        self.s = requests.Session()

    def login(self) -> bool:
        if self.logged_in or (time.time() - self.last_login_check_time
                              ) < 60:  # Check interval: 60 seconds
            return self.logged_in

        payload = {
            "Email": self.username,
            "Password": self.password,
        }

        response = self.s.post(self.url + "/LogIn", data=payload)
        html = response.content.decode("utf-8")

        if html.find("Log out") == -1:
            self.logged_in = False
        else:
            self.logged_in = True

        self.last_login_check_time = time.time(
        )  # Update last login check time
        return self.logged_in

    def check_login(self) -> None:
        res = self.s.get(self.url)
        html = res.content.decode("utf-8")

        if html.find("Log out") == -1:
            self.logged_in = False
        else:
            self.logged_in = True

    def get_data(self) -> str:
        res = self.s.get(self.url + "/System/169626/Status/ServiceInfo")
        return res.content.decode("utf-8")

    def replace_chars(self, metric_name) -> str:
        return re.sub(r"[ -.,]+", "_", metric_name)

    def create_metrics(self):
        if not self.logged_in or (time.time() -
                                  self.last_login_check_time) >= 60:
            self.check_login()  # Check login status periodically
            self.last_login_check_time = time.time(
            )  # Update last login check time

        html = self.get_data()
        match = r"^[-+]?\d+[,.]?\d*"
        soup = BeautifulSoup(html, features="html.parser")

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

                metric = self.metric_dict.get(metric_name)
                if metric is None:
                    metric = Gauge(metric_name, "")
                    self.metric_dict[metric_name] = metric

                if isinstance(value, (int, float)):
                    metric.set(value)

    def main(self):
        frequency = 15
        exporter_port = int(environ.get("EXPORTER_PORT", "9877"))
        start_http_server(exporter_port, addr='0.0.0.0')
        logging.warning(f"Listening on 0.0.0.0:{exporter_port}")

        logging.warning(f"Logging in to {self.url}")
        if not self.login():
            print("Couldn't login. Exiting.")
            exit(1)

        logging.warning("Script started to listen for incoming requests.")

        while True:
            self.create_metrics()
            time.sleep(frequency)


if __name__ == "__main__":
    url = "https://www.nibeuplink.com"
    username = environ.get("NIBE_USERNAME")
    password = environ.get("NIBE_PASSWORD")

    if not (username and password):
        print("You need to define the NIBE_USERNAME and NIBE_PASSWORD "
              "environment variables.")
        exit(1)

    c = CustomExporter(url, username, password)
    c.main()
