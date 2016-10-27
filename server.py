#!/usr/bin/python
# -*- coding: utf-8 -*-
import socket


class Response:
    def __init__(self, type):
        self.main_header = "HTTP/1.1 %d", type
        self.headers = []

    def add_header(self, string):
        self.headers.append(string)

    def add_body_site(self, filename):
        pass

    def add_body_image(self, filename):
        pass

    def respond(self):
        response = self.main_header + "\n\r\n\r"
        for h in self.headers:
            response += h + "\n\r"
        response += "Con"
        return response


def main():
    sock= socket.socket()
    sock.bind(("", 8000))
    sock.listen(10)

    while True:
        conn, addr = sock.accept()
        data = conn.recv(16384).decode('utf-8')
        query = data.split('\r\n')[0]
        print("Query: %s" % query)
        query = query.split(' ')

        if query[0] == "GET":
            if query[1] == "/":
                # response = Response(200)
                # response.add_body_site('server.html')
                file = open('server.html', 'r', encoding='utf-8').read()
                answer = ("HTTP/1.1 200\r\n\r\n%s\r\n" % file).encode('utf-8')
            elif ".ico" in query[1]:
                file = open('%s' % query[1][1:], 'r').read()
                answer = ("HTTP/1.1 200\r\n\r\n%s\r\n" % file).encode('utf-8')
            else:
                file = open('%s' % query[1][1:], 'r', encoding='utf-8').read()
                answer = ("HTTP/1.1 200\r\n\r\n%s\r\n" % file).encode('utf-8')

            conn.send(answer)

        conn.close()

if __name__ == "__main__":
    main()