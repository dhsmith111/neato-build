from gpiozero import OutputDevice
import serial
import threading
import time
import os


class Neato:
    """Serial interface to Neato XV via USB with relay power cycle support."""

    def __init__(self, port='/dev/ttyACM0', baud=115200, relay_pin=17):
        self.port = port
        self.baud = baud
        self.relay = OutputDevice(relay_pin, active_high=True, initial_value=True)
        self.ser = None
        self._lock = threading.Lock()

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
        """Send a command and return the response as a string. Thread-safe."""
        if not self.ser or not self.ser.is_open:
            raise ConnectionError("Serial port not open — call connect() or power_cycle() first")
        with self._lock:
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

    # --- Sensor commands ---

    def get_digital_sensors(self):
        """Return digital sensor values as a dict."""
        raw = self.send('GetDigitalSensors', delay=0.3)
        sensors = {}
        for line in raw.strip().split('\n'):
            if ',' in line and not line.startswith('Digital'):
                parts = line.split(',')
                if len(parts) >= 2:
                    sensors[parts[0].strip()] = int(parts[1].strip())
        return sensors

    def get_analog_sensors(self):
        """Return analog sensor values as a dict."""
        raw = self.send('GetAnalogSensors', delay=0.3)
        sensors = {}
        for line in raw.strip().split('\n'):
            if ',' in line and not line.startswith('Sensor'):
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        sensors[parts[0].strip()] = int(parts[1].strip())
                    except ValueError:
                        pass
        return sensors

    def get_accel_parsed(self):
        """Return accelerometer as dict with float values."""
        raw = self.send('GetAccel', delay=0.3)
        accel = {}
        for line in raw.strip().split('\n'):
            if ',' in line and not line.startswith('Label'):
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        accel[parts[0].strip()] = float(parts[1].strip())
                    except ValueError:
                        pass
        return accel

    def play_sound(self, sound_id):
        """Play a built-in sound (0-20). TestMode only."""
        return self.send(f"PlaySound SoundID {sound_id}", delay=0.1)

    def set_led(self, *args):
        """Set LED state. TestMode only. e.g. set_led('ButtonGreen', 'BlinkOn')"""
        return self.send(f"SetLED {' '.join(args)}", delay=0.1)