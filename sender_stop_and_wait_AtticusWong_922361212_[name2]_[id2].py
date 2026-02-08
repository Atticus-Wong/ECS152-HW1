import socket
import time


HOST = "127.0.0.1"

RECEIVER_PORT = 5001
SENDER_PORT = 5000

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4

def open_file():
    with open('starter/docker/file.mp3', 'rb') as f:
        contents = f.read()
        return contents

def test_socket_connection():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("localhost", SENDER_PORT))

    m = b"hello world"

    sock.sendto(m, ("localhost", RECEIVER_PORT))

    data, addr = sock.recvfrom(1028) 
    
    print(f"Received packet from {addr}")
    # Decode the data (assuming it's a UTF-8 string)
    print(f"Message: {data.decode('utf-8')}")


def solve():
    stored_data = []
    contents = open_file()
    for i in range(0, len(contents), 1020):  
        stored_data.append(contents[i:i+1020])
    print(len(stored_data))
    start = time.time() # throughput timer
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("localhost", SENDER_PORT))
    sock.settimeout(2.0)
    idx = 0
    packetDelays = []
    while idx < len(contents):
        seq_id = idx.to_bytes(4, byteorder='big')
        packet = seq_id + stored_data[idx // 1020]
        packetStart = time.time()
        sock.sendto(packet, ("localhost", RECEIVER_PORT)) # per packet delay timer starts here
        try:
            data, addr = sock.recvfrom(1028) 
            # per packet delay timer stops here
            packetStop = time.time()
            ack_id = int.from_bytes(data[:4], byteorder='big')
            print(f"Received ACK from {addr}")
            print(f"ACK ID (next expected byte): {ack_id}")
            packetDelays.append(packetStop - packetStart)
            idx = ack_id
        except socket.timeout:  
            time.sleep(2)
        
    end = time.time() # throughput timer
    print(f"Total time to send all packets: {end - start}")

    throughput, perPacketDelay = start - end, sum(packetDelays) / len(packetDelays)

    print("Throughput: ", start - end)
    print("Per Packet Delay: ", perPacketDelay)
    print("Final Score:", 0.3*throughput/1000 + 0.7/perPacketDelay)
if __name__ == "__main__":
    solve()
