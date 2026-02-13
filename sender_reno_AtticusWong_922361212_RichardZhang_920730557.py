import time
import socket

HOST = "127.0.0.1"

RECEIVER_PORT = 5001
SENDER_PORT = 5000

PACKET_SIZE = 1024
MESSAGE_SIZE = 1020
SEQ_ID_SIZE = 4

TIMEOUT = 3


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
    sock.settimeout(TIMEOUT)

    next_send_seq = 0
    last_ack_seq = 0
    ack_time = {} #ack seq -> time received
    sent_time = {} #packet seq -> time sent, first transmission only
    cwnd = 1
    ssthresh = 64
    fast_recovery_flag = False

    dup_acks = 0


    while last_ack_seq < len(contents):
        while (next_send_seq - last_ack_seq) // MESSAGE_SIZE < cwnd and next_send_seq < len(contents):
            # Send as many packets as the window allows
            seq_id = next_send_seq.to_bytes(4, byteorder='big')
            packet = seq_id + stored_data[next_send_seq // MESSAGE_SIZE]
            sock.sendto(packet, ("localhost", RECEIVER_PORT))
            if next_send_seq not in sent_time:
                sent_time[next_send_seq] = time.time()
            next_send_seq += MESSAGE_SIZE
        try:
            data, addr = sock.recvfrom(PACKET_SIZE)
            ack_id = int.from_bytes(data[:4], byteorder='big')

            if ack_id == last_ack_seq:
                dup_acks += 1

                if dup_acks == 3:
                    ssthresh = max(cwnd // 2, 1)
                    cwnd = ssthresh
                    # enter fast recovery. we increment cwnd by 1 for each dup ack
                    fast_recovery_flag = True
                    cwnd += 3

                    seq_id = last_ack_seq.to_bytes(4, byteorder='big')
                    packet = seq_id + stored_data[last_ack_seq // MESSAGE_SIZE]
                    sock.sendto(packet, ("localhost", RECEIVER_PORT)) # fast retransmit
                elif dup_acks > 3 and fast_recovery_flag:
                    cwnd += 1
            elif ack_id > last_ack_seq:
                for seq in range(last_ack_seq, ack_id, MESSAGE_SIZE):
                    ack_time[seq] = time.time()
                dup_acks = 0
                last_ack_seq = ack_id
                if fast_recovery_flag:
                    cwnd = ssthresh # reset to ssthresh instead of 1
                    fast_recovery_flag = False
                else:
                    if cwnd < ssthresh: # slow start
                        cwnd += 1 # cwnd grows exponentially, per ack received
                    else: # congestion avoidance
                        cwnd += 1 / cwnd # cwnd grows linearly, increment 1 MSS per RTT (we receive cwnd acks per RTT)
        except socket.timeout: # havent't received packet in time, shrink window to size 1
            dup_acks = 0
            ssthresh = max(cwnd // 2, 1)
            cwnd = 1
            next_send_seq = last_ack_seq
            fast_recovery_flag = False


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
    

    throughput, per_pkt_delay = len(contents) / (end - start), sum(packet_delays) / len(packet_delays)
    final_score = 0.3*throughput/1000 + 0.7/per_pkt_delay if per_pkt_delay > 0 else 0
    print(f"Throughput: {throughput:.7f}")
    print(f"Per Packet Delay: {per_pkt_delay:.7f}")
    print(f"Final Score: {final_score:.7f}")


if __name__ == "__main__":
    solve()
