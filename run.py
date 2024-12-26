import numpy as np
import matplotlib.pyplot as plt
import threading
import queue
from scipy.special import erfc

# Tham số mô phỏng
num_bits = 8  # Số lượng bit dữ liệu gốc trong mỗi gói tin
polynomial = '1101'  # Đa thức CRC
timeout = 2  # Thời gian chờ ACK (Acknowledgment)
max_retransmissions = 5  # Số lần truyền lại tối đa

ack_received = threading.Event()
simulation_done = threading.Event()  # Sự kiện cho biết mô phỏng đã hoàn tất
BER_results = []

# Hàng đợi để truyền dữ liệu giữa sender và receiver
network_queue = queue.Queue()

# --- CRC ---
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

def validate_crc(data_with_crc, polynomial=polynomial):
    data_with_crc_bitstring = ''.join(map(str, data_with_crc))
    remainder = crc_remainder(data_with_crc_bitstring, polynomial)
    return int(remainder) == 0

# --- Mã Hamming ---
def hamming_encode(data_with_crc):
    if len(data_with_crc) != 7:
        raise ValueError("Dữ liệu đầu vào phải có 7 bit (4 bit dữ liệu và 3 bit CRC).")
    # Hamming (7,4) Generator Matrix (G)
    G = np.array([[1, 1, 0, 1],
                  [1, 0, 1, 1],
                  [1, 0, 0, 0],
                  [0, 1, 1, 1],
                  [0, 1, 0, 0],
                  [0, 0, 1, 0],
                  [0, 0, 0, 1]])

    data_bits = data_with_crc[:4]  # 4 data bits
    crc_bits = data_with_crc[4:]   # 3 CRC bits
    encoded_data = np.dot(G, data_bits) % 2
    encoded_data = np.concatenate((encoded_data, crc_bits))  # Append CRC bits to encoded data
    return encoded_data

def hamming_decode(encoded_data_with_crc):
    # Extract encoded data and CRC bits
    encoded_data = encoded_data_with_crc[:7]  # 7 bits Hamming encoded data
    crc_bits = encoded_data_with_crc[7:]     # 3 bits CRC

    if len(encoded_data) != 7:
        raise ValueError("Dữ liệu đầu vào phải có 7 bit")
    
    # Hamming(7,4) Check Matrix (H)
    H = np.array([[1, 0, 1, 0, 1, 0, 1],
                  [0, 1, 1, 0, 0, 1, 1],
                  [0, 0, 0, 1, 1, 1, 1]])

    # Calculate the syndrome (error detection)
    syndrome = np.dot(H, encoded_data) % 2
    error_position = int(''.join(map(str, syndrome)), 2)  # Convert syndrome to error position

    # If there is an error (syndrome != 0), correct it
    if error_position != 0:
        encoded_data[error_position - 1] ^= 1  # Flip the bit at the error position (1-based index)

    # Extract the 4 data bits after correction
    data_bits = np.array([encoded_data[2], encoded_data[4], encoded_data[5], encoded_data[6]])
    dencoded_data = np.concatenate ([data_bits, crc_bits])

    return dencoded_data

# --- Chuyển đổi chéo ---
def interleave(codewords):
    interleaved = []
    for i in range(len(codewords[0])):
        interleaved.append([cw[i] for cw in codewords])
    return np.array(interleaved).flatten()

def deinterleave(codewords, original_length):
    deinterleaved = []
    for i in range(original_length):
        deinterleaved.append(codewords[i::original_length])
    return np.array(deinterleaved).flatten()

# --- Kênh truyền ---
def channel(tx_signal, SNR):
    noise = np.random.normal(0, np.sqrt(1/(2 * SNR)), tx_signal.shape)
    rx_signal = tx_signal + noise
    return np.where(rx_signal > 0.5, 1, 0)

# --- Hoạt động HARQ ---
def sender(data_packets):
    for sequence_number, packet in enumerate(data_packets):
        retransmission_count = 0
        while retransmission_count <= max_retransmissions:
            data_bits = packet[:4]  # Lấy 4 bit dữ liệu
            packet_with_crc = append_crc(data_bits)  # Thêm CRC vào gói tin
            encoded_packet = hamming_encode(packet_with_crc)  # Mã hóa gói tin với CRC
            interleaved_packet = interleave([encoded_packet])  # Xen kẽ gói tin
            
            # Đưa gói tin vào hàng đợi để gửi
            network_queue.put((sequence_number, interleaved_packet))
            print(f"@ Sender: Gửi gói tin {sequence_number} ---- lần thứ {retransmission_count + 1}")
            
            ack_received.clear()  # Xóa trạng thái ACK cũ
            ack_received.wait(timeout=timeout)  # Chờ ACK trong khoảng thời gian timeout

            if ack_received.is_set():  # Nếu nhận được ACK
                break
            else:
                retransmission_count += 1
                print(f"Sender: Không nhận được ACK cho gói tin {sequence_number}. Gửi lại gói tin.")
                
            if retransmission_count == max_retransmissions:
                print(f"----Sender: Gửi lại gói tin {sequence_number} quá số lần cho phép.----") 
                break
    simulation_done.set()  # Đánh dấu mô phỏng đã hoàn tất



# --- Kết hợp gói tin (Chase Combining) ---
# def chase_combine(previous_signals, current_signal):
#     """
#     Kết hợp các gói tin bằng cách tính giá trị trung bình của các bit từ các lần truyền trước và lần truyền hiện tại.
#     """
#     combined_signal = np.zeros_like(current_signal)
#     for i in range(len(current_signal)):
#         # Tính trung bình có trọng số của các bit nhận được từ các lần truyền trước
#         combined_signal[i] = np.mean([previous_signals[j][i] for j in range(len(previous_signals))] + [current_signal[i]])
#     return np.where(combined_signal > 0.5, 1, 0)


# --- Receiver with Chase Combining ---
def receiver_with_combining(data_packets, SNR):
    retransmissions = {}
    combined_signal = None  # Initialize the combined signal variable

    while True:
        if not network_queue.empty():
            sequence_number, encoded_packet = network_queue.get()
            print(f"Receiver: Nhận gói tin {sequence_number}")

            # Perform channel decoding
            received_signal = channel(encoded_packet, SNR)
            deinterleaved_packet = deinterleave(received_signal, len(data_packets))

            # Perform Chase Combining: Combine current and previous received signals
            if combined_signal is None:
                combined_signal = deinterleaved_packet
            else:
                combined_signal = np.maximum(combined_signal, deinterleaved_packet)

            # Decoding after combining
            decoded_packet = hamming_decode(combined_signal)
            if validate_crc(decoded_packet):
                print(f"$$$ Receiver: Gửi ACK về Sender của gói tin {sequence_number} $$$")
                ack_received.set()
                combined_signal = None  # Reset after successful decoding
            else:
                print(f"Receiver: Gửi NACK về Sender của gói tin {sequence_number}")
                if sequence_number not in retransmissions:
                    retransmissions[sequence_number] = 0
                retransmissions[sequence_number] += 1

        if simulation_done.is_set():
            break

# --- Mô phỏng HARQ với Hamming, CRC và Chase Combining ---
def simulate_harq_hamming_crc_chase_combining(SNR):
    data_to_send = [np.random.randint(0, 2, num_bits) for _ in range(10)]
    sender_thread = threading.Thread(target=sender, args=(data_to_send,))
    receiver_thread = threading.Thread(target=receiver_with_combining, args=(data_to_send,SNR))

    receiver_thread.start()
    sender_thread.start()

    sender_thread.join()
    receiver_thread.join()
simulate_harq_hamming_crc_chase_combining(1)
