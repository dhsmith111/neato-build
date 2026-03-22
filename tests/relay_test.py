from gpiozero import OutputDevice
import time

relay = OutputDevice(17, active_high=True, initial_value=False)

print("Closing relay (VBUS connected)...")
relay.on()
time.sleep(2)

print("Opening relay (VBUS disconnected)...")
relay.off()
time.sleep(1)

print("Done.")