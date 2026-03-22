from gpiozero import OutputDevice
import serial
import time
import os

RELAY_PIN = 17
PORT = '/dev/ttyACM0'

relay = OutputDevice(RELAY_PIN, active_high=True, initial_value=False)
print("Opening relay (cutting VBUS)...")
relay.off()

# Wait for port to disappear
print("Waiting for port to disappear...")
timeout = 10
elapsed = 0
while os.path.exists(PORT) and elapsed < timeout:
    time.sleep(0.5)
    elapsed += 0.5
print(f"Port gone after {elapsed}s")

time.sleep(3)

print("Closing relay (restoring VBUS)...")
relay.on()

# Now wait for port to reappear
print("Waiting for port to reappear...")
timeout = 30
elapsed = 0
while not os.path.exists(PORT) and elapsed < timeout:
    time.sleep(0.5)
    elapsed += 0.5

if not os.path.exists(PORT):
    print("Port never reappeared — check wiring")
    relay.off()
    exit(1)

print(f"Port reappeared after {elapsed}s — settling...")
time.sleep(3)

print("Opening serial connection...")
ser = serial.Serial(PORT, 115200, timeout=2)
time.sleep(1)

print("Sending GetVersion...")
ser.write(b'GetVersion\n')
time.sleep(1)

response = ser.read(ser.in_waiting)
print("Response:", response.decode('utf-8', errors='replace'))

ser.close()
relay.off()
print("Done.")