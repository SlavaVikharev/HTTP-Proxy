import re
import time
import socket
import socket_ext
import select
import argparse
import threading
from thread_pool import ThreadPool


# Ignore regexs list
#
IGNORE_FILE = 'ignore_list.txt'
ignore_list = []


def watch_ignore(delay=1):
    global ignore_list

    while True:
        try:
            with open(IGNORE_FILE) as f:
                lines = f.read().splitlines()
                lines = filter(lambda l: not l.startswith('#'), lines)
                ignore_list = list(map(re.compile, lines))
        except FileNotFoundError:
            ignore_list = []
        time.sleep(delay)


# Proxy
#
WORKERS = 200
BUFF_SIZE = 4096

lock = threading.Lock()

HOST_RE = re.compile(r'Host: ([^\s]+)')

BAD_REQ = b"""
HTTP/1.1 400 Bad Request
Connection: Close

"""


def get_host(request):
    host = HOST_RE.search(request)
    if host is None:
        return None, None

    host = host.group(1)
    if ':' in host:
        host, port = host.split(':')
        port = int(port)
    else:
        port = 80

    return host, port


def proxy_connection(conn, client_addr):
    request = conn.recv(BUFF_SIZE)
    decoded = request.decode()

    fst_line = decoded.splitlines()[0].split()

    type_ = fst_line[0]
    if type_.upper() == 'CONNECT':
        conn.send(BAD_REQ)
        conn.close()
        return

    url = fst_line[1]
    if url.startswith('https'):
        conn.send(BAD_REQ)
        conn.close()
        return

    host, port = get_host(decoded)
    if host is None:
        conn.send(BAD_REQ)
        conn.close()
        return

    with lock:
        print(host, port)
        print(url)
        print()

    for rex in ignore_list:
        if not rex.search(url):
            continue

        conn.send(BAD_REQ)
        conn.close()
        return

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            sock.send(request)
            sock.resendall(conn, buff_size=BUFF_SIZE)
    except socket.error:
        pass
    finally:
        conn.close()


def proxy_server(host, port):
    addr = host, port

    tp = ThreadPool(WORKERS)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            sock.bind(addr)
            sock.listen(WORKERS)

            print('Listening on', addr)

            while True:
                if not select.select([sock], [], [], 1)[0]:
                    continue

                conn, client_addr = sock.accept()
                tp.add_task(proxy_connection, conn, client_addr)
    except socket.error:
        print('Cannot run the server')

    tp.wait_completion()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default='localhost')
    parser.add_argument('--port', type=int, default=8001)
    args = parser.parse_args()

    threading.Thread(target=watch_ignore, daemon=True).start()

    proxy_server(args.host, args.port)
