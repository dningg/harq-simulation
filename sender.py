import socket
import numpy as np
import time

# Max transmission attempts
MAX_TRANSMISSION = 4
timeout = 1
polynomial = "1101"

# CRC calculation
def crc_remainder(input_bitstring, polynomial_bitstring):
    polynomial_bitstring = polynomial_bitstring.lstrip('0')
    len_input = len(input_bitstring)
    input_padded_array = list(input_bitstring + '0' * (len(polynomial_bitstring) - 1))
    while '1' in input_padded_array[:len_input]:
        cur_shift = input_padded_array.index('1')
        for i in range(len(polynomial_bitstring)):
            input_padded_array[cur_shift + i] = str(int(polynomial_bitstring[i] != input_padded_array[cur_shift + i]))
    remainder = ''.join(input_padded_array)[len_input:]
    return remainder

def append_crc(data, polynomial=polynomial):
    data_bitstring = ''.join(map(str, data))
    crc = crc_remainder(data_bitstring, polynomial)
    data_with_crc = data_bitstring + crc
    return np.array([int(x) for x in data_with_crc])


# Hamming encode/decoder
def hamming_encode(data_with_crc):
    data_bits = data_with_crc[:64]  # 64 data bits
    crc_bits = data_with_crc[64:]   # 3 CRC bits

    if len(data_bits) != 64:
        raise ValueError("Dữ liệu đầu vào phải có 64 bit")

    # Tạo mảng 64 bit, chèn dữ liệu vào các vị trí không phải 2^i
    encoded_bits = np.zeros(71, dtype=int)
    data_index = 0
    for i in range(71):
        if (i + 1) & i != 0:  # Loại bỏ các vị trí 2^i (1, 2, 4, 8, 16, 32, 64)
            encoded_bits[i] = data_bits[data_index]
            data_index += 1

    # Tính các bit kiểm tra
    for i in range(7):  # Có 7 bit kiểm tra tại các vị trí 2^i
        parity_pos = 2**i - 1
        parity_value = 0
        for j in range(71):
            if (j + 1) & (parity_pos + 1) != 0:
                parity_value ^= encoded_bits[j]
        encoded_bits[parity_pos] = parity_value

    encoded_data = np.concatenate((encoded_bits, crc_bits))  # Append CRC bits to encoded data
    return encoded_data


def sender(packets, server_ip, server_port, timeout=timeout):
    sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sender_socket.connect((server_ip, server_port))
    
    # Set timeout for socket operations
    sender_socket.settimeout(timeout)
    
    for packet in packets:
        print(f"[Sender] Data to send: {packet}")
        data_with_crc = append_crc(packet)  # Add CRC
        print(f"[Sender] Data with CRC: {data_with_crc}")
        encoded_data = hamming_encode(data_with_crc)  # Hamming encode
        print(f"[Sender] Encoded data (Hamming): {encoded_data}")
        
        attempt = 0
        while attempt < MAX_TRANSMISSION:
            print(f"[Sender] Sending data (attempt {attempt + 1})...")
            sender_socket.sendall(encoded_data.tobytes())
            
            try:
                response = sender_socket.recv(1024).decode()
                
                if response == "ACK":
                    print("[Sender] ACK received. Moving to next packet.")
                    break

                elif response == "NACK":
                    print("[Sender] NACK received. Resending data...")
                    attempt += 1
                else:
                    print("[Sender] Unknown response. Resending data...")
                    attempt += 1
            except socket.timeout:
                print(f"[Sender] Timeout occurred. No response received in {timeout} seconds. Retrying...")
                attempt += 1

            if attempt == MAX_TRANSMISSION:
                print("[Sender] Max transmission attempts reached. Skipping to next packet.")

    print("---[Sender] All packets sent. Closing connection.---")
    sender_socket.close()

if __name__ == "__main__":
    server_ip = "127.0.0.1"
    server_port = 5055
    # Example packet generation
    data = [np.random.randint(0, 2, 64) for _ in range(56)]
    np.save('data_original.npy', data)
    sender(data, server_ip, server_port)
    time.sleep(1)
