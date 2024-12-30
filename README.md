# HARQ (Hybrid Automatic Repeat Request) Simulation by Python

The HARQ simulation in the code above utilizes techniques such as **Cyclic Redundancy Check (CRC)** and **Hamming code** to ensure data integrity during transmission over a network. This simulation demonstrates how HARQ ensures that even when errors occur during transmission, data is reliably sent through encoding and retransmission mechanisms.

## Workflow:

### **Sender**
1. **Data Preparation**:
   - Generates fake data (64 bits) and appends a CRC checksum for error detection.
2. **Hamming Encoding**:
   - Encodes the data (with CRC) using Hamming code by adding parity bits for error correction.
3. **Data Transmission**:
   - Sends the encoded data via a TCP socket to the receiver.
   - Retransmits the packet up to **4 attempts** (`MAX_TRANSMISSION`) if no valid acknowledgment is received from the receiver.

### **Receiver**
1. **Simulate Packet Loss and Bit Errors**:
   - Introduces packet loss (`loss_packet`) and bit errors (`error`) to simulate a noisy environment.
2. **Hamming Decoding**:
   - Decodes the received data using Hamming code and corrects errors if possible.
3. **CRC Check**:
   - Verifies the integrity of the decoded data using the CRC checksum.
   - Sends an acknowledgment:
     - **"ACK"**: If the decoded data is valid.
     - **"NACK"**: If the decoded data fails the CRC check.
4. **Handle Corrupted Packets**:
   - If a packet fails multiple transmissions, the corrupted data is stored after reaching the maximum retransmission limit.

This HARQ simulation demonstrates how encoding (Hamming code) and retransmission (ARQ) work together to ensure reliable data transmission, even in error-prone networks.
