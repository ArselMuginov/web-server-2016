#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
TCP server with basic authentication
"""

import datetime
import os
import socket
from base64 import b64decode
from threading import Thread

MIME_TYPES = {
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tiff": "image/tiff",
    ".pdf": "application/pdf",
    ".webm": "video/webm",
    ".txt": "text/plain",
}

DATA_SIZE = 16384
REALM = "arsel.muginov@gmail.com"

AUTH_BASE = {
    "arsel": "123",
    "bob": "alice",
}


class Query:
    """
    Represents a query that server receives from the client
    """
    def __init__(self, data):
        """
        Creates a query by parsing headers and content from received data
        :param data: received information from the client, text with CRLF separators
        """
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

    def authenticated(self):
        """
        Checks if the client is authenticated.
        Basic authentication is used.
        :return: True if the client is authenticated and False for opposite
        """
        if 'Authorization' in self.headers:
            auth_type, encoded = self.headers['Authorization'].split(' ')[-2:]
            if auth_type == 'Basic':
                user, password = b64decode(encoded.encode('utf-8')).decode('utf-8').split(':', 1)
                if user in AUTH_BASE and AUTH_BASE[user] == password:
                    return True
        return False


class Response:
    """
    Represents a response that server sends to the client
    """
    def __init__(self, status_code):
        """
        Creates a response using a status code
        :param status_code: HTTP response status code
        """
        self.main_header = "HTTP/1.1 %d" % status_code
        self.headers = []
        self.content = None

    def add_header(self, key, value):
        """
        Adds a header in response with format <key>: <value>
        """
        self.headers.append("%s: %s" % (key, value))

    def add_content(self, filename):
        """
        Adds a content in response in binary format.
        It is guaranteed that the file exists.
        :param filename: path to the file starting from server root
        """
        file = open(filename, "rb")
        self.content = file.read()
        file.close()

        for mime in MIME_TYPES:
            if filename.endswith(mime):
                self.add_header("Content-type", MIME_TYPES[mime])
                break

        self.add_header("Content-size", len(self.content))

    def respond(self):
        """
        Transforms all headers to a string in binary,
        then sends it with the content
        :return: two strings in binary: headers and a content
        """
        all_headers = self.main_header + "\r\n"
        for h in self.headers:
            all_headers += "%s\r\n" % h
        all_headers += "\r\n"
        return all_headers.encode('utf-8'), self.content


def log(msg):
    """
    Prints a message about server work with reference to the time.
    :param msg: message that needs to be printed
    """
    print("[%s] %s" % (datetime.datetime.now(), msg))


def client_handle(client, address):
    """
    Handles the work with the client:
    receives data, processes it, and sends the result back.
    :param client: socket representing the connection
    :param address: address of the client
    """
    try:
        query = Query(client.recv(DATA_SIZE).decode('utf-8'))

        if query.empty:
            return

        log("RECV : %s" % query.headers_raw.replace('\r\n', ' | '))

        if query.authenticated():
            if os.path.exists(query.main_header["path"]):
                response = Response(200)
                response.add_content(query.main_header["path"])
            else:
                return
        else:
            response = Response(401)
            response.add_header('WWW-Authenticate', 'Basic realm="%s"' % REALM)

        headers, content = response.respond()
        client.send(headers)
        client.send(content)
        log("SENT : %s" % headers.decode('utf-8').replace('\r\n', ' | '))
        client.close()

    except Exception as e:
        client.close()
        log("EXC : %s" % e)


def main():
    """
    Entry point.
    Creates socket and waits for the client in a loop.
    When a client connects, its handling is performed in another thread.
    That allows handling multiple clients.
    """
    sock = socket.socket()
    sock.bind(("", 8000))
    sock.listen(10)

    while True:
        client, address = sock.accept()
        Thread(target=client_handle, args=(client, address)).start()


if __name__ == "__main__":
    main()
