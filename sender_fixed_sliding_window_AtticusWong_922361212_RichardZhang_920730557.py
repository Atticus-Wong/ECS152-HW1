import time
import socket


HOST = "127.0.0.1"

RECEIVER_PORT = 5001
SENDER_PORT = 5000

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4

def open_file():
    with open('starter/docker/file.mp3', 'rb') as f:
        contents = f.read()
        return contents

def solve():
    stored_data = []
    contents = open_file()
    for i in range(0, len(contents), 1020):  
        stored_data.append(contents[i:i+1020])
    start = time.time() # throughput timer
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("localhost", SENDER_PORT))
    sock.settimeout(2.0)

if __name__ == "__main__":
    solve()
