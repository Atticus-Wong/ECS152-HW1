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
    sock.settimeout(1)

    last_sent = 0
    last_received = 0
    received_packets = {} #id -> time received
    sent_packets = {} #id -> time received

    dup_acks = 0


    while last_received < len(contents):
        while (last_sent - last_received) // MESSAGE_SIZE < WINDOW_SIZE and last_sent < len(contents):
            seq_id = last_sent.to_bytes(4, byteorder='big')
            packet = seq_id + stored_data[last_sent // MESSAGE_SIZE]
            sock.sendto(packet, ("localhost", RECEIVER_PORT))
            #print(f"Sending seq id {last_sent}")
            print(f"Sent {last_sent//MESSAGE_SIZE}th packet")
            last_sent += MESSAGE_SIZE
            sent_packets[last_sent // MESSAGE_SIZE] = time.time()
        try:
            data, addr = sock.recvfrom(PACKET_SIZE)
            ack_id = int.from_bytes(data[:4], byteorder='big')
            received_packets[ack_id // MESSAGE_SIZE] = time.time()

            #print(f"ack id: {ack_id//MESSAGE_SIZE}")
            #print(f"last_received: {last_received//MESSAGE_SIZE}\n")
            if ack_id == last_received:
                print("X")
                dup_acks += 1
                if dup_acks == 3:
                    #Fast retransmit
                    seq_id = ack_id.to_bytes(4, byteorder='big')
                    packet = seq_id + stored_data[ack_id // MESSAGE_SIZE]
                    sock.sendto(packet, ("localhost", RECEIVER_PORT))
                    #print(f"Fast retransmit packet {ack_id // MESSAGE_SIZE} (dup ACK {ack_id})")
            elif ack_id > last_received:
                dup_acks = 0
                # Cumulative ACK: receiver advanced past expected, advance window
                last_received = ack_id
                print(f"Received ACK {last_received//MESSAGE_SIZE}th packet")
        except socket.timeout:
            last_sent = last_received
            dup_acks = 0
            print("TIMEOUT")

    end = time.time()
    print("ending connection")
    empty_message = last_received.to_bytes(4, byteorder="big")
    sock.sendto(empty_message, ("localhost", RECEIVER_PORT))

    while True:
        try:
            data, addr = sock.recvfrom(PACKET_SIZE)
            msg = data[4:]
            print(msg)
            if b"fin" in msg:
                break
        except socket.timeout:
            sock.sendto(empty_message, ("localhost", RECEIVER_PORT))
    
    finack = int.to_bytes(0, 4, byteorder="big") + b"==FINACK=="
    sock.sendto(finack, ("localhost", RECEIVER_PORT))
    sock.close()



if __name__ == "__main__":
    solve()
