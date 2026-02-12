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
TIMEOUT = 0.5

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


    dup_acks = 0

    num_timeouts = 0
    num_fast_retransmits = 0
    num_cum_dup_acks = 0
    fast_retransmit_freq_map = defaultdict(int) #seq id -> freq

    while last_ack_seq < len(contents):
        while (next_send_seq - last_ack_seq) // MESSAGE_SIZE < WINDOW_SIZE and next_send_seq < len(contents):
            seq_bytes = next_send_seq.to_bytes(4, byteorder="big")
            packet = seq_bytes + stored_data[next_send_seq // MESSAGE_SIZE]
            sock.sendto(packet, ("localhost", RECEIVER_PORT))
            print(f"Sent {next_send_seq//MESSAGE_SIZE}th packet")
            if next_send_seq not in sent_time:
                sent_time[next_send_seq] = time.time()
            outstanding_packets[next_send_seq] = time.time()
            next_send_seq += MESSAGE_SIZE
        try:
            data, addr = sock.recvfrom(PACKET_SIZE)
            ack_id = int.from_bytes(data[:4], byteorder="big")

            if ack_id == last_ack_seq:
                num_cum_dup_acks += 1
                dup_acks += 1

                if dup_acks == 3:
                    #Fast retransmit
                    print(f"FAST RETRANSMIT {last_ack_seq // MESSAGE_SIZE}th packet")
                    seq_bytes = last_ack_seq.to_bytes(4, byteorder="big")
                    packet = seq_bytes + stored_data[last_ack_seq // MESSAGE_SIZE]
                    sock.sendto(packet, ("localhost", RECEIVER_PORT))
                    num_fast_retransmits += 1
                    fast_retransmit_freq_map[last_ack_seq  // MESSAGE_SIZE] += 1
                    outstanding_packets[last_ack_seq] = time.time()
            elif ack_id > last_ack_seq:
                dup_acks = 0
                # Cumulative ACK: all packets up to last_ack_seq have been acked.
                for seq in range(last_ack_seq, ack_id, MESSAGE_SIZE):
                    ack_time[seq] = time.time()
                    del outstanding_packets[seq] # delete this packet since it is no longer in flight
                last_ack_seq = ack_id
                print(f"Received ACK up to {last_ack_seq//MESSAGE_SIZE}th packet")
        except socket.timeout:
            pass

        now = time.time()
        if last_ack_seq in outstanding_packets and now - TIMEOUT >= outstanding_packets[last_ack_seq]: # if oldest packet has exceeded timeout, selectively retransmit it
            seq_bytes = last_ack_seq.to_bytes(4, byteorder="big")
            packet = seq_bytes + stored_data[last_ack_seq // MESSAGE_SIZE]
            sock.sendto(packet, ("localhost", RECEIVER_PORT))
            outstanding_packets[last_ack_seq] = time.time() # refresh its timeout

    end = time.time()
    print("\nentering termination protocol")
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

    sorted_acks = sorted(list(ack_time.keys()))

    #calculate per packet delays
    packet_delays = []
    for packet in sent_time:
        for ack in sorted_acks:
            if ack > packet:
                delay = ack_time[ack] - sent_time[packet]
                packet_delays.append(delay)
                break
    

    throughput, per_pkt_delay = len(contents) / (end - start), sum(packet_delays) / len(packet_delays)
    print("Throughput: ", throughput)
    print("Per Packet Delay: ", per_pkt_delay)
    print("Final Score:", 0.3*throughput/1000 + 0.7/per_pkt_delay)


    #print("\nADDITIONAL STATS:")
    #print("Number of timeouts:", num_timeouts)
    #print("Number of cumulative duplicate acks:", num_cum_dup_acks)
    #print("Number of fast retransmits:", num_fast_retransmits)
    #if fast_retransmit_freq_map:
    #    print("Frequency map of fast retransmits:", fast_retransmit_freq_map)


if __name__ == "__main__":
    solve()
