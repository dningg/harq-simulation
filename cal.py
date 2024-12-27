import numpy as np
import matplotlib.pyplot as plt

# Load the original and received data arrays
data_original = np.load('data_original.npy', allow_pickle=True)
data_receiver = np.load('data_receiver.npy', allow_pickle=True)

# Check the shape of the arrays
print(f"Original data shape: {data_original.shape}")
print(f"Received data shape: {data_receiver.shape}")

# Ensure that both arrays have the same number of packets
if len(data_original) != len(data_receiver):
    raise ValueError(f"Different number of packets: {len(data_original)} vs {len(data_receiver)}")

# Initialize lists to store BER values for each packet
ber_per_packet = []

# Loop through each packet and calculate the BER
for i in range(len(data_original)):
    original_packet = np.array(data_original[i]).flatten()
    received_packet = np.array(data_receiver[i]).flatten()

    # Debug print to check the lengths of each packet
    print(f"Packet {i} - Original length: {len(original_packet)}, Received length: {len(received_packet)}")

    # Ensure the lengths of both packets are the same
    if len(original_packet) != len(received_packet):
        raise ValueError(f"Packet {i} has different lengths.")

    # Calculate the number of bit errors
    bit_errors = np.count_nonzero(original_packet != received_packet)

    # Calculate the total number of bits
    total_bits = len(original_packet)

    # Calculate the Bit Error Rate (BER)
    ber = bit_errors / total_bits
    ber_per_packet.append(ber)

# Plot the BER for each packet
plt.figure(figsize=(10, 6))
plt.plot(range(1, len(ber_per_packet) + 1), ber_per_packet, marker='o', linestyle='-', color='b')
plt.title('Bit Error Rate (BER) for Each Packet')
plt.xlabel('Packet Number')
plt.ylabel('Bit Error Rate (BER)')
plt.grid(True)
plt.show()
