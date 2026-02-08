import time
import socket


HOST = "127.0.0.1"

RECEIVER_PORT = 5001
SENDER_PORT = 5000

PACKET_SIZE = 1024
MESSAGE_SIZE = 1020
SEQ_ID_SIZE = 4

WINDOW_SIZE = 100

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

    last_sent = 0
    last_received = 0
    while last_received < len(contents):
        while (last_sent - last_received) // MESSAGE_SIZE < WINDOW_SIZE and last_sent < len(contents):
            seq_id = last_sent.to_bytes(4, byteorder='big')
            packet = seq_id + stored_data[last_sent // MESSAGE_SIZE]
            sock.sendto(packet, ("localhost", RECEIVER_PORT))
            #print(f"Sending seq id {last_sent}")
            print(f"Sent {last_sent//MESSAGE_SIZE}th packet")
            last_sent += MESSAGE_SIZE
        try:
            data, addr = sock.recvfrom(1028)
            ack_id = int.from_bytes(data[:4], byteorder='big')
            #print(f"ACK ID (next expected byte): {ack_id}")
            if ack_id > last_received:
                last_received = ack_id
                print(f"Received {last_received//MESSAGE_SIZE}th packet")
        except socket.timeout:  
            #time.sleep(2)
            last_sent = last_received
            print("TIMEOUT")

        """
        1 2 3 4 5
        1 2   4 5
            3 4 5
            3 
        """

        

if __name__ == "__main__":
    solve()
