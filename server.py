#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import socket
from threading import Thread
import datetime

MIME_TYPES = {
    "gif": "image/gif",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "tiff": "image/tiff",
    "pdf": "application/pdf",
    "webm": "video/webm",
}

DATA_SIZE = 16384

class Query:
    def __init__(self, data):
        if len(data) == 0:
            self.empty = True
            return
        else:
            self.empty = False

        headers, content = data.split('\r\n\r\n')
        self.headers_raw = headers
        headers = headers.split('\r\n')

        main_header = headers[0].split(' ')
        self.main_header = {
            "method": main_header[0],
            "path": main_header[1][1:] if main_header[1] != "/" else "server.html",
            "protocol": main_header[2],
        }

        self.headers = {k: v for [k, v] in [header.split(':', 1) for header in headers[1:]]}
        self.content = content


class Response:
    def __init__(self, type):
        self.main_header = "HTTP/1.1 %d" % type
        self.headers = []

    def add_header(self, key, value):
        self.headers.append("%s:%s" % (key, value))

    def add_content(self, filename):
        file = open(filename, "rb")
        self.content = file.read()
        file.close()

        for mime in MIME_TYPES:
            if filename.endswith(mime):
                self.add_header("Content-type", MIME_TYPES[mime])
                break

        self.add_header("Content-size", len(self.content))

    def respond(self):
        all_headers = self.main_header + "\r\n"
        for h in self.headers:
            all_headers += "%s\r\n" % h
        all_headers += "\r\n"
        return all_headers.encode('utf-8'), self.content


def main():
    sock = socket.socket()
    sock.bind(("", 8000))
    sock.listen(10)

    while True:
        client, address = sock.accept()
        Thread(target=client_handle, args=(client, address)).start()


def client_handle(client, address):
    while True:
        try:
            query = Query(client.recv(DATA_SIZE).decode('utf-8'))

            if query.empty:
                return

            log("RECV : %s" % query.headers_raw.replace('\r\n', ' | '))

            if os.path.exists(query.main_header["path"]):
                response = Response(200)
                response.add_content(query.main_header["path"])
                response.add_header("Connection", "keep-alive")
            else:
                return

            headers, content = response.respond()
            client.send(headers)
            client.send(content)
            log("SENT : %s" % headers.decode('utf-8').replace('\r\n', ' | '))

        except Exception as e:
            client.close()
            log("EXC : %s" % e)
            return False

def log(msg):
    print("[%s] %s" % (datetime.datetime.now(), msg))

if __name__ == "__main__":
    main()
