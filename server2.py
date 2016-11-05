#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
TCP server with authentication using forms and cookies
"""

import datetime
import os
import socket
import time
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

AUTH_BASE = {
    "arsel": "123",
    "bob": "alice",
    "alice": "bob",
}

DATA_SIZE = 16384
REALM = "arsel.muginov@gmail.com"

PAGES = {
    "root": "server.html",
    "auth": "auth.html",
    "404": "404.html",
}


class Get:
    """
    Class used for get methods from the client
    """

    class Auth:
        """
        Authentication methods
        """

        @staticmethod
        def login(client_params):
            """
            Looks for a user in authentication database.
            If the pair user:password matched with the pair in database,
            then it creates server parameters for response.
            Otherwise, it just declares an error.
            :param client_params: dictionary of parameters set by submitting a form
            :return: (True, server parameters) for passed authentication
                     (False, None) for opposite.
            """
            try:
                if AUTH_BASE[client_params['user']] == client_params['password']:
                    # TODO: rewrite code to look more obvious
                    expires = time.time() + 14 * 24 * 3600  # 14 days from now
                    str_expires = time.strftime("%a, %d %b %Y %T GMT", time.gmtime(expires))
                    server_params = {
                        'Set-Cookie': [
                            'user=%s; Expires=%s; Path=/' % (client_params['user'], str_expires),
                            'password=%s; Expires=%s; Path=/' % (client_params['password'], str_expires),
                        ]
                    }
                    return True, server_params
                else:
                    return False, None
            except KeyError:
                return False, None


CLASS_REGISTRY = {
    'GET': Get
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
            "path": main_header[1][1:],
            "protocol": main_header[2],
        }

        self.headers = {k: v for [k, v] in [header.split(': ', 1) for header in headers[1:]]}
        self.content = content

    def resolve_path(self):
        """
        Resolves path from main_header:
        for root path replaces it with root page;
        for get method replaces it with requested method;
        for server file replaces it with path to the file.
        If get method or file is not exists, then it declares an error
        :return: a tuple where first means path to the file or method pointer
                 second is used in method only: get parameters from a form
        """
        path = self.main_header["path"]

        if path == "":
            return PAGES["root"], None

        try:
            iterator = CLASS_REGISTRY[self.main_header["method"]]
            clean_path, params = path.split('?', 1)
            for subpath in clean_path.split('/'):
                iterator = getattr(iterator, subpath)
            params = {k: v for [k, v] in [param.split('=', 1) for param in params.split('&')]}
            return iterator, params

        except (KeyError, AttributeError, ValueError):
            return (path, None) if os.path.exists(path) else (None, None)

    def authenticated(self):
        """
        Checks if the client is authenticated.
        Authentication checked by comparing a cookies with the server data.
        :return: True if the client is authenticated and False for opposite
        """
        try:
            cookies = {k: v for [k, v] in [cookie.split('=', 1) for cookie in self.headers['Cookie'].split('; ')]}
            if AUTH_BASE[cookies['user']] == cookies['password']:
                return True
            else:
                return False
        except KeyError:
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

        path, client_params = query.resolve_path()
        if client_params is not None:
            ok, server_params = path(client_params)
            if ok:
                response = Response(200)
                for param in server_params:
                    for value in server_params[param]:
                        response.add_header(param, value)
                response.add_content(PAGES["root"])
            else:
                response = Response(401)
                response.add_content(PAGES["auth"])
        elif path is not None:
            if query.authenticated():
                response = Response(200)
                response.add_content(path)
            else:
                response = Response(401)
                response.add_content(PAGES["auth"])
        else:
            response = Response(404)
            response.add_content(PAGES["404"])

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
