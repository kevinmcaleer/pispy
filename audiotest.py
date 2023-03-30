import machine
import network
import socket
import time
from machine import I2S
from machine import Pin
import array

# Connect to Wi-Fi
WIFI_SSID = "Home"
WIFI_PASSWORD = "bleelady1234"

print('starting up')
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASSWORD)

while not wlan.isconnected():
    print('.',end="")
    time.sleep(0.25)

print("Connected to Wi-Fi")
print(wlan.ifconfig())

# I2S configuration
SAMPLE_RATE = 16000
BITS_PER_SAMPLE = 16

i2s = I2S(
    0,
    sck=Pin(16),
    ws=Pin(17),
    sd=Pin(18),
    mode=I2S.RX,
    bits=BITS_PER_SAMPLE,
    format=I2S.MONO,
    rate=SAMPLE_RATE,
    ibuf=4000
)

# Create a socket
addr = socket.getaddrinfo("0.0.0.0", 8000)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
print("Listening on", addr)

buffer_size = 1024
buff = bytearray(buffer_size)

def amplify_audio(buffer, gain):
    audio_format = 'h' if BITS_PER_SAMPLE == 16 else 'B'
    audio_samples = array.array(audio_format, buffer)
    for i in range(len(audio_samples)):
        audio_samples[i] = min(max(int(audio_samples[i] * gain), -2**(BITS_PER_SAMPLE-1)), 2**(BITS_PER_SAMPLE-1)-1)
    amplified_buffer = bytearray(audio_samples)
    return amplified_buffer

# def amplify_audio(buffer, gain):
#     num_samples = len(buffer) // 3
#     amplified_buffer = bytearray(num_samples * 3)
#     for i in range(num_samples):
#         sample = int.from_bytes(buffer[i*3:i*3+3], 'little', signed=True)
#         amplified_sample = min(max(int(sample * gain), -2**(BITS_PER_SAMPLE-1)), 2**(BITS_PER_SAMPLE-1)-1)
#         amplified_buffer[i*3:i*3+3] = int.to_bytes(amplified_sample, 3, 'little', signed=True)
#     return amplified_buffer

def generate_wav_header(sample_rate, bits_per_sample, num_channels):
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    wav_header = b'RIFF----WAVEfmt \x10\x00\x00\x00\x01\x00' + \
                 num_channels.to_bytes(2, 'little') + \
                 sample_rate.to_bytes(4, 'little') + \
                 byte_rate.to_bytes(4, 'little') + \
                 block_align.to_bytes(2, 'little') + \
                 bits_per_sample.to_bytes(2, 'little') + \
                 b'data----'
    return wav_header

wav_header = generate_wav_header(SAMPLE_RATE, BITS_PER_SAMPLE, 1)

# Stream audio over HTTP
while True:
    client, addr = s.accept()
    print("Client connected from:", addr)
    client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: audio/wav\r\n\r\n")
    client.sendall(wav_header)
    
    while True:
        try:
            num_read = i2s.readinto(buff)
#             print('read data',num_read)
            if num_read > 0:
                amplified_buff = amplify_audio(buff,2)
#                 print('data sent', str(buff))
                client.sendall(amplified_buff)
        except OSError as e:
            print('error',e)
            break

    print("Client disconnected")
    client.close()
