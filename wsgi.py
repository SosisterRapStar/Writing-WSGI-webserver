import io
import socket
from typing import List
import sys



class WSGIServer:
    IP_family = socket.AF_INET  # использется IPv4
    transport_proto = socket.SOCK_STREAM  # это TCP сокет
    buffer_size = 4096  # размер буфера, размер буфера лучше делать степенью двойки

    def __init__(self, host: str, port: int):
        self.connection = None
        self.client_addr = None
        self.host = host
        self.port = port

        self.my_socket = socket.socket(self.IP_family, self.transport_proto)  # оздается сам сокет в sockets
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # для переиспользования порта

        self.my_socket.bind((self.host, self.port))  # биндим
        self.server_name = socket.getfqdn(host)  # возвращает полное доменное имя для сокет

        self.headers_set = []  # такой параметр есть в PEP 333 это хедеры, которые должен отправить фреймворк
        # в start response

    def serve_forever(self):  # сокет слушает подключения
        self.my_socket.listen()
        while True:
            self.connection, client_addr = self.my_socket.accept()
            self.manage_request()  # обрабатывает запрос, возвращает ответ и закрывает соединение

    def get_environ(self):
        env = {}
        # WSGI
        env['wsgi.version'] = (1, 0)
        env['wsgi.url_scheme'] = 'http'
        env['wsgi.input'] = io.StringIO(self.data_from_request)  # тут должен быть какой-то поток, в моем случае поток
        # ввода-вывода
        env['wsgi.errors'] = sys.stderr
        env['wsgi.multithread'] = False
        env['wsgi.multiprocess'] = False
        env['wsgi.run_once'] = False
        # Какая-то шняга для CGI
        env['REQUEST_METHOD'] = self.request_method
        env['PATH_INFO'] = self.path
        env['SERVER_NAME'] = self.server_name
        env['SERVER_PORT'] = str(self.port)

    def set_app(self, application):  # принимает объект стороны приложения используется при конфигурации объекта сервера
        self.application = application

    # парсинг будет переделан в более нормальный
    def parse_request(self, text):
        request_line = text.splitlines()[0]
        request_line = request_line.rstrip('\r\n')

        (self.request_method,
         self.path,
         self.request_version
         ) = request_line.split()

    def manage_request(self):
        data_from_request = self.connection.recv(self.buffer_size).decode('utf-8')
        self.data_from_request = data_from_request

        print(''.join(f'{line}\n' for line in data_from_request.splitlines()))

        self.parse_request(data_from_request)

        env = self.get_environ()  # возвратит словарь с параметрами CGI и WSGI, которые нужно передать приложению

        result = self.application(env, self.start_response)

        self.send_response(result)

    # Функция start_response согласно PEP 333 должна быть имплементирована на стороне сервера в интерфейсе WSGI
    # Сторона фреймворка должна принять объект этой функции вроде как
    def start_response(self, status, response_headers, exc_info=None):
        # статус ответа дает сторона приложение, также как и заголовки ответа
        self.headers_set = [status, response_headers]
        return ... # согласно PEP здесь должен возвращаться объект функции send_response/write

    # Функция для ответа
    def send_response(self, result): # В PEP 333 эта функция называется write
        try:
            status, response_headers = self.headers_set

            response = f'HTTP/1.1 {status}\r\n'


            for header in response_headers:
                response += '{0}: {1}\r\n'.format(*header)
            response += '\r\n' # пустая строка между заголовками и телом
            # result - это результат, который отдало приложение
            for data in result:
                response += data.decode('utf-8')  # заполнение тела


            print(''.join(f'{line}\n' for line in response.splitlines()))  # принт в консоль, почему бы нет

            response_bytes = response.encode()

            self.connection.sendall(response_bytes)  # отправляет ответ от приложение HTTP серверу
        finally:
            self.connection.close()


d = WSGIServer('localhost', 4000)
