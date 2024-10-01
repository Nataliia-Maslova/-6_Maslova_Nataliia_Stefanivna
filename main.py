from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from multiprocessing import Process
import mimetypes
import json
import urllib.parse
import pathlib
import socket
import logging

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb://mongodb:27017"

HTTPServer_Port = 3000
UDP_IP = '127.0.0.1'
UDP_PORT = 5000



# Клас для HTTP-сервера
class HttpGetHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == '/':
            self.send_html_file('index.html')
        elif parsed_path.path == '/message.html':
            self.send_html_file('message.html')
        elif parsed_path.path.startswith('/static/'):
            self.send_static()
        else:
            self.send_html_file('error.html', status_code=404)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        parsed_data = urllib.parse.parse_qs(body.decode())
        username = parsed_data.get('username')[0]
        message = parsed_data.get('message')[0]
        
        # Підготовка даних для відправки на сокет-сервер
        data = json.dumps({
            "username": username,
            "message": message,
            "date": str(datetime.now())
        }).encode()

        send_data_to_socket(data)

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def send_html_file(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        file_path = pathlib.Path(filename)
        self.wfile.write(file_path.read_bytes())

    def send_static(self):
        self.send_response(200)
        mime_type, _ = mimetypes.guess_type(self.path)
        self.send_header('Content-type', mime_type)
        self.end_headers()
        static_path = pathlib.Path(self.path[1:])
        self.wfile.write(static_path.read_bytes())


def run_http_server(server_class=HTTPServer, handler_class=HttpGetHandler):
    server_address = ('0.0.0.0', HTTPServer_Port)
    http = server_class(server_address, handler_class)
    logging.info("Starting HTTP server")
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        logging.info("Stopping HTTP server")
        http.server_close()


def send_data_to_socket(data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data, (UDP_IP, UDP_PORT))
    sock.close()

def save_data(data):
    client = MongoClient(uri, server_api=ServerApi("1"))
    db = client.messages_db
    messages_collection = db.messages

    message_data = json.loads(urllib.parse.unquote_plus(data.decode()))
    message_data['date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    messages_collection.insert_one(message_data)
    

def run_socket_server(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    logging.info("Starting Socket server")
    try:
        while True:
            data, address = sock.recvfrom(1024)
            logging.info(f"Received data: {data} from {address}")
            save_data(data)
    except KeyboardInterrupt:
        logging.info("Stopping Socket server")
    finally:
        sock.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(threadName)s %(message)s')

    # Запуск HTTP-сервера і Socket-сервера в різних процесах
    http_server_process = Process(target=run_http_server)
    socket_server_process = Process(target=run_socket_server, args=(UDP_IP, UDP_PORT))

    http_server_process.start()
    socket_server_process.start()

    http_server_process.join()
    socket_server_process.join()

