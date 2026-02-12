import time
import socket
from collections import defaultdict


HOST = "127.0.0.1"

RECEIVER_PORT = 5001
SENDER_PORT = 5000

PACKET_SIZE = 1024
MESSAGE_SIZE = 1020
SEQ_ID_SIZE = 4

WINDOW_SIZE = 100
TIMEOUT = 3

def open_file():
    with open("starter/docker/file.mp3", "rb") as f:
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
    sock.settimeout(0.1)

    next_send_seq = 0
    last_ack_seq = 0
    ack_time = {} #ack -> time received
    sent_time = {} #packet id -> time sent, only first send
    outstanding_packets = {} #packet id in flight -> time sent, latest send

    while last_ack_seq < len(contents):
        while (next_send_seq - last_ack_seq) // MESSAGE_SIZE < WINDOW_SIZE and next_send_seq < len(contents):
            # Send as many packets as the window allows
            seq_bytes = next_send_seq.to_bytes(4, byteorder="big")
            packet = seq_bytes + stored_data[next_send_seq // MESSAGE_SIZE]
            sock.sendto(packet, ("localhost", RECEIVER_PORT))
            if next_send_seq not in sent_time:
                sent_time[next_send_seq] = time.time()
            outstanding_packets[next_send_seq] = time.time()
            next_send_seq += MESSAGE_SIZE
        try:
            data, addr = sock.recvfrom(PACKET_SIZE) # Try to receive an ack within timeout, otherwise 
            ack_id = int.from_bytes(data[:4], byteorder="big")

            if ack_id > last_ack_seq:
                # Cumulative ACK: all packets up to last_ack_seq have been acked.
                for seq in range(last_ack_seq, ack_id, MESSAGE_SIZE):
                    ack_time[seq] = time.time()
                    del outstanding_packets[seq] # delete this packet since it is no longer in flight
                last_ack_seq = ack_id
        except socket.timeout: 
            pass


        # For every packet in current window, check if it
        # has been in flight for longer than TIMEOUT.
        # If so, retransmit it and reset its timer
        now = time.time()
        for seq in range(last_ack_seq, next_send_seq, MESSAGE_SIZE):
            if seq in outstanding_packets and now - outstanding_packets[seq] >= TIMEOUT:
                seq_bytes = seq.to_bytes(4, byteorder="big")
                packet = seq_bytes + stored_data[seq // MESSAGE_SIZE]
                sock.sendto(packet, ("localhost", RECEIVER_PORT))
                outstanding_packets[seq] = time.time() # refresh its timeout

    # End the connection by sending an empty message, receive fin, and send finack
    end = time.time()
    empty_message = last_ack_seq.to_bytes(4, byteorder="big")
    sock.sendto(empty_message, ("localhost", RECEIVER_PORT))

    while True:
        try:
            data, addr = sock.recvfrom(PACKET_SIZE)
            msg = data[4:]
            if b"fin" in msg:
                break
        except socket.timeout:
            sock.sendto(empty_message, ("localhost", RECEIVER_PORT))
    
    finack = int.to_bytes(0, 4, byteorder="big") + b"==FINACK=="
    sock.sendto(finack, ("localhost", RECEIVER_PORT))
    sock.close()

    #calculate per packet delays
    packet_delays = []
    for seq in sent_time:
        if seq in ack_time:
            packet_delays.append(ack_time[seq] - sent_time[seq])
        
    # print results
    throughput, per_pkt_delay = len(contents) / (end - start), sum(packet_delays) / len(packet_delays)
    final_score = 0.3*throughput/1000 + 0.7/per_pkt_delay
    print(f"Throughput: {throughput:.7f}")
    print(f"Per Packet Delay: {per_pkt_delay:.7f}")
    print(f"Final Score: {final_score:.7f}")


if __name__ == "__main__":
    solve()
