import time
import socket
from collections import defaultdict

"""
Useful resources: 
    - https://book.systemsapproach.org/congestion/tcpcc.html
    - https://canvas.ucdavis.edu/courses/1058429/files/folder/Lecture%20Slides?preview=29802473
        - slide 18. maybe has incorrect info about what to do on timeout. slide says divide cwnd by 2 
        but google and textbook say reset cwnd to 1
    - https://www.geeksforgeeks.org/computer-networks/tcp-reno-with-example/
"""

HOST = "127.0.0.1"

RECEIVER_PORT = 5001
SENDER_PORT = 5000

PACKET_SIZE = 1024
MESSAGE_SIZE = 1020
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
    sock.settimeout(1)

    next_send_seq = 0
    last_ack_seq = 0
    received_acks = {} #ack -> time received
    sent_packets = {} #packet -> time received
    cwnd = 1
    ssthresh = 100
    fast_recovery_flag = False

    dup_acks = 0

    num_timeouts = 0
    num_fast_retransmits = 0
    num_cum_dup_acks = 0
    fast_retransmit_freq_map = defaultdict(int) #seq id -> freq

    while last_ack_seq < len(contents):
        while (next_send_seq - last_ack_seq) // MESSAGE_SIZE < cwnd and next_send_seq < len(contents):
            seq_id = next_send_seq.to_bytes(4, byteorder='big')
            packet = seq_id + stored_data[next_send_seq // MESSAGE_SIZE]
            sock.sendto(packet, ("localhost", RECEIVER_PORT))
            print(f"Sent {next_send_seq//MESSAGE_SIZE}th packet")
            if next_send_seq not in sent_packets:
                sent_packets[next_send_seq] = time.time()
            next_send_seq += MESSAGE_SIZE
        try:
            data, addr = sock.recvfrom(PACKET_SIZE)
            ack_id = int.from_bytes(data[:4], byteorder='big')
            if ack_id not in received_acks:
                received_acks[ack_id] = time.time()

            if ack_id == last_ack_seq:
                num_cum_dup_acks += 1
                dup_acks += 1

                if dup_acks == 3:
                    #Fast retransmit
                    print(f"FAST RETRANSMIT {last_ack_seq // MESSAGE_SIZE}th packet")
                    print("ENTERING FAST RECOVERY")
                    ssthresh = max(cwnd // 2, 1)
                    cwnd = ssthresh
                    print(f"New cwnd: {cwnd}. New thresh: {ssthresh}")
                    # enter fast recovery. we increment cwnd by 1 for each dup ack
                    fast_recovery_flag = True
                    cwnd += 3

                    seq_id = last_ack_seq.to_bytes(4, byteorder='big')
                    packet = seq_id + stored_data[last_ack_seq // MESSAGE_SIZE]
                    sock.sendto(packet, ("localhost", RECEIVER_PORT))
                    num_fast_retransmits += 1
                    fast_retransmit_freq_map[last_ack_seq  // MESSAGE_SIZE] += 1
                elif dup_acks > 3 and fast_recovery_flag:
                    print(f"Fast recovery, cwnd: {cwnd}")
                    cwnd += 1
            elif ack_id > last_ack_seq:
                dup_acks = 0
                last_ack_seq = ack_id
                print(f"Received ACK up to {last_ack_seq//MESSAGE_SIZE}th packet")
                if fast_recovery_flag:
                    cwnd = ssthresh # reset to ssthresh instead of 1
                    print(f"Exiting fast recovery. Setting cwnd to {cwnd}")
                    fast_recovery_flag = False
                else:
                    if cwnd < ssthresh: # slow start
                        cwnd += 1 # cwnd grows exponentially
                        print(f"Slow start, cwnd: {cwnd}")
                    else: # congestion avoidance
                        cwnd += 1 / cwnd # cwnd grows linearly, increment 1 MSS per RTT (we receive cwnd acks per RTT)
                        print(f"Congestion avoidance, cwnd: {cwnd}")

        except socket.timeout:
            dup_acks = 0
            num_timeouts += 1
            ssthresh = max(cwnd // 2, 1)
            cwnd = 1
            next_send_seq = last_ack_seq
            print(f"TIMEOUT. thresh: {ssthresh}, cwnd: 1. Resending from {next_send_seq//MESSAGE_SIZE}")



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


    #print("\nADDITIONAL STATS:")
    #print("Number of timeouts:", num_timeouts)
    #print("Number of cumulative duplicate acks:", num_cum_dup_acks)
    #print("Number of fast retransmits:", num_fast_retransmits)
    #if fast_retransmit_freq_map:
    #    print("Frequency map of fast retransmits:", fast_retransmit_freq_map)


if __name__ == "__main__":
    solve()
