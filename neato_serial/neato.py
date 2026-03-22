from gpiozero import OutputDevice
import serial
import time
import os


class Neato:
    """Serial interface to Neato XV via USB with relay power cycle support."""

    def __init__(self, port='/dev/ttyACM0', baud=115200, relay_pin=17):
        self.port = port
        self.baud = baud
        self.relay = OutputDevice(relay_pin, active_high=True, initial_value=True)
        self.ser = None

    def power_cycle(self, off_time=3, settle_time=3, reappear_timeout=30):
        """Cut VBUS via relay, wait for port to drop and reappear, then connect."""
        self.close()

        # Cut VBUS
        self.relay.off()

        # Wait for port to disappear
        elapsed = 0
        while os.path.exists(self.port) and elapsed < 10:
            time.sleep(0.5)
            elapsed += 0.5

        time.sleep(off_time)

        # Restore VBUS
        self.relay.on()

        # Wait for port to reappear
        elapsed = 0
        while not os.path.exists(self.port) and elapsed < reappear_timeout:
            time.sleep(0.5)
            elapsed += 0.5

        if not os.path.exists(self.port):
            raise TimeoutError(f"{self.port} did not reappear after {reappear_timeout}s")

        time.sleep(settle_time)
        self.connect()

    def connect(self):
        """Open serial connection."""
        self.ser = serial.Serial(self.port, self.baud, timeout=2)
        time.sleep(1)

    def close(self):
        """Close serial connection if open."""
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.ser = None

    def shutdown(self):
        """Close serial and cut VBUS."""
        self.close()
        self.relay.off()

    def send(self, command, delay=0.5):
        """Send a command and return the response as a string."""
        if not self.ser or not self.ser.is_open:
            raise ConnectionError("Serial port not open — call connect() or power_cycle() first")
        self.ser.reset_input_buffer()
        self.ser.write(f"{command}\n".encode())
        time.sleep(delay)
        response = self.ser.read(self.ser.in_waiting)
        return response.decode('utf-8', errors='replace')

    # --- Common commands ---

    def get_version(self):
        return self.send('GetVersion')

    def get_charger(self):
        return self.send('GetCharger')

    def get_accel(self):
        return self.send('GetAccel')

    def set_lds_rotation(self, on=True):
        return self.send(f"SetLDSRotation {'On' if on else 'Off'}")

    def get_lds_scan(self):
        return self.send('GetLDSScan', delay=1)

    def test_mode(self, on=True):
        return self.send(f"TestMode {'On' if on else 'Off'}")

    def set_motor(self, left_dist=0, right_dist=0, speed=100):
        """Drive wheels. Distances in mm, speed in mm/s."""
        return self.send(
            f"SetMotor LWheelDist {left_dist} RWheelDist {right_dist} Speed {speed}"
        )

    def set_config(self, key, value):
        return self.send(f"SetConfig {key} {value}")