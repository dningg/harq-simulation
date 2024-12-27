import socket
import numpy as np
import random

# Max transmission attempts
MAX_TRANSMISSION = 4
polynomial = "1101"
loss_packet = 0.1
error = 0.02

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

def validate_crc(data_with_crc, polynomial=polynomial):
    data_with_crc_bitstring = ''.join(map(str, data_with_crc))
    remainder = crc_remainder(data_with_crc_bitstring, polynomial)
    return int(remainder) == 0

# Hamming encode/decoder
def hamming_decode(encoded_data_with_crc):
    encoded_data = np.array(encoded_data_with_crc[:71], copy=True)  # Tạo bản sao có thể chỉnh sửa
    crc_bits = encoded_data_with_crc[71:]  # CRC bits

    if len(encoded_data) != 71:
        raise ValueError("Dữ liệu đầu vào phải có 71 bit")
    
    # Ma trận kiểm tra H (7 x 71)
    H = np.array([[int(bit) for bit in format(i + 1, '07b')] for i in range(71)]).T

    # Tính hội chứng (syndrome)
    syndrome = np.dot(H, encoded_data) % 2
    error_position = int(''.join(map(str, syndrome)), 2)  # Chuyển hội chứng sang vị trí lỗi

    # Nếu có lỗi (error_position != 0), sửa lỗi
    corrected_bits = encoded_data.copy()

    if error_position != 0:
        if error_position <= len(corrected_bits):  # Kiểm tra vị trí lỗi có hợp lệ không
            corrected_bits[error_position - 1] ^= 1  # Lật bit tại vị trí lỗi
        else:
            print(f"[Receiver] Error position {error_position} is out of bounds, skipping correction.")
            return None  # Trả về None nếu vị trí lỗi không hợp lệ

    # Loại bỏ các bit kiểm tra (chỉ lấy 64 bit dữ liệu)
    decoded_bits = []
    for i in range(71):
        if (i + 1) & i != 0:  # Loại bỏ các vị trí 2^i
            decoded_bits.append(corrected_bits[i])

    # Extract data bits after correction
    data_bits = np.array(decoded_bits)
    decoded_data = np.concatenate([data_bits, crc_bits])

    return decoded_data


# Receiver function with packet loss and bit error simulation
def receiver(host_ip, host_port, loss_packet=loss_packet, error=error):
    receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    receiver_socket.bind((host_ip, host_port))
    receiver_socket.listen(1)
    
    print(f"[Receiver] Listening on {host_ip}:{host_port}...")
    conn, addr = receiver_socket.accept()
    print(f"[Receiver] Connected by {addr}")
    
    total_packets = 0
    lost_packets = 0
    combined_signal = None  # Initialize combined_signal variable

    while True:
        received_data = conn.recv(512)
        if not received_data:
            break

        # Mô phỏng mất gói tin
        if random.random() < loss_packet:
            lost_packets += 1
            total_packets += 1
            print("[Receiver] Packet lost")
            continue  # Không xử lý gói tin nếu bị mất
        
        encoded_data = np.frombuffer(received_data, dtype=np.uint8)
        print(f"---[Receiver] Received data from sender---")
        print(f"[Receiver] Data length: {len(encoded_data)}")

        encoded_data = encoded_data.tolist()[::4]
        
        # Mô phỏng lỗi bit
        corrupted_data = []
        for bit in encoded_data:
            corrupted_bit = bit
            if random.random() < error:
                corrupted_bit = 1 - bit  # Nếu bit = 0 thì đổi thành 1, nếu bit = 1 thì đổi thành 0
            corrupted_data.append(corrupted_bit)
        
        # Combine the corrupted data if there's already data stored in combined_signal
        if combined_signal is None:
            combined_signal = corrupted_data
        else:
            combined_signal = np.maximum(combined_signal, corrupted_data)  # Combine using maximum (bitwise OR)

        try:
            decoded_data_with_crc = hamming_decode(corrupted_data)
            if decoded_data_with_crc is None:
                print("[Receiver] Skipping corrupted data due to invalid error position.")
                total_packets += 1
                continue

            if validate_crc(decoded_data_with_crc):
                print("[Receiver] CRC validation passed. Sending ACK...")
                combined_signal = None
                conn.sendall("ACK".encode())

            else:
                print("[Receiver] CRC validation failed. Sending NACK...")
                conn.sendall("NACK".encode())
                
        except ValueError as e:
            print(f"[Receiver] Decoding error: {e}. Sending NACK...")
            conn.sendall("NACK".encode())

        total_packets += 1
    
    print("------------@@[Receiver] Closing connection@@------------")
    print(f"[Receiver] Total packets received: {total_packets}")
    print(f"[Receiver] Lost packets: {lost_packets}")
    
    receiver_socket.close()


if __name__ == "__main__":
    host_ip = "127.0.0.1"
    host_port = 5055
    receiver(host_ip, host_port, loss_packet, error)
