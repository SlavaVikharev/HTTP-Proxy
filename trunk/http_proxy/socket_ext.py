import socket
import select


def resendall(from_, to, timeout=1, buff_size=4096):
    while True:
        if not select.select([from_], [], [], timeout)[0]:
            break

        buffer = from_.recv(buff_size)
        to.send(buffer)

        if not buffer:
            break

socket.socket.resendall = resendall
