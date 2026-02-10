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

    last_sent_seq = 0
    last_received_seq = 0
    received_acks = {} #ack -> time received
    sent_packets = {} #packet -> time received

    dup_acks = 0

    num_timeouts = 0
    num_fast_retransmits = 0
    num_cum_dup_acks = 0
    fast_retransmit_freq_map = defaultdict(int) #seq id -> freq

    while last_received_seq < len(contents):
        while (last_sent_seq - last_received_seq) // MESSAGE_SIZE < WINDOW_SIZE and last_sent_seq < len(contents):
            seq_id = last_sent_seq.to_bytes(4, byteorder='big')
            packet = seq_id + stored_data[last_sent_seq // MESSAGE_SIZE]
            sock.sendto(packet, ("localhost", RECEIVER_PORT))
            print(f"Sent {last_sent_seq//MESSAGE_SIZE}th packet")
            if last_sent_seq not in sent_packets:
                sent_packets[last_sent_seq] = time.time()
            last_sent_seq += MESSAGE_SIZE
        try:
            data, addr = sock.recvfrom(PACKET_SIZE)
            ack_id = int.from_bytes(data[:4], byteorder='big')
            if ack_id not in received_acks:
                received_acks[ack_id] = time.time()

            #print(f"ack id: {ack_id//MESSAGE_SIZE}")
            #print(f"last_received_seq: {last_received_seq//MESSAGE_SIZE}\n")
            if ack_id == last_received_seq:
                print(f"DUP ACK")
                num_cum_dup_acks += 1
                dup_acks += 1
                if dup_acks == 3:
                    #Fast retransmit
                    print(f"FAST RETRANSMIT {ack_id // MESSAGE_SIZE}th packet")
                    seq_id = ack_id.to_bytes(4, byteorder='big')
                    packet = seq_id + stored_data[ack_id // MESSAGE_SIZE]
                    sock.sendto(packet, ("localhost", RECEIVER_PORT))
                    num_fast_retransmits += 1
                    fast_retransmit_freq_map[ack_id  // MESSAGE_SIZE] += 1
                    dup_acks = 0
            elif ack_id > last_received_seq:
                dup_acks = 0
                # Cumulative ACK: receiver advanced past expected, advance window
                last_received_seq = ack_id
                print(f"Received ACK {last_received_seq//MESSAGE_SIZE}th packet")
        except socket.timeout:
            last_sent_seq = last_received_seq
            dup_acks = 0
            num_timeouts += 1
            print("TIMEOUT")

    end = time.time()
    print("entering termination protocol")
    empty_message = last_received_seq.to_bytes(4, byteorder="big")
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

    sorted_acks = sorted(list(received_acks.keys()))

    #calculate per packet delays
    packet_delays = []
    for packet in sent_packets:
        for ack in sorted_acks:
            if ack > packet:
                delay = received_acks[ack] - sent_packets[packet]
                packet_delays.append(delay)
                break
    

    throughput, per_pkt_delay = len(contents) / (end - start), sum(packet_delays) / len(packet_delays)
    print("Throughput: ", throughput)
    print("Per Packet Delay: ", per_pkt_delay)
    print("Final Score:", 0.3*throughput/1000 + 0.7/per_pkt_delay)


    print("\nADDITIONAL STATS:")
    print("Number of timeouts:", num_timeouts)
    print("Number of cumulative duplicate acks:", num_cum_dup_acks)
    print("Number of fast retransmits:", num_fast_retransmits)
    if fast_retransmit_freq_map:
        print("Frequency map of fast retransmits:", fast_retransmit_freq_map)


if __name__ == "__main__":
    solve()
