"""Background sensor polling thread for Neato hardware sensors."""

import threading
import time
from dataclasses import dataclass, field


@dataclass
class SensorState:
    """Snapshot of all hardware sensor readings."""
    # Bumpers
    bumper_left_front: bool = False
    bumper_right_front: bool = False
    bumper_left_side: bool = False
    bumper_right_side: bool = False

    # Cliff / drop
    left_drop_mm: int = 0
    right_drop_mm: int = 0

    # Wheel drop (robot lifted)
    left_wheel_extended: bool = False
    right_wheel_extended: bool = False

    # Wall proximity
    wall_distance_mm: int = 9999

    # Battery
    battery_voltage_mv: int = 0
    battery_temp_c: int = 0
    current_ma: int = 0

    # Charger / dock
    on_charger: bool = False
    dustbin_in: bool = True

    # Accelerometer
    pitch_degrees: float = 0.0
    roll_degrees: float = 0.0

    # Mag sensors (dock proximity?)
    left_mag: int = 0
    right_mag: int = 0

    @property
    def any_bumper(self):
        return (self.bumper_left_front or self.bumper_right_front or
                self.bumper_left_side or self.bumper_right_side)

    def any_cliff(self, baseline_mm=60, threshold_mm=5):
        """Cliff detected when drop reading exceeds baseline + threshold.

        On flat ground the sensors read ~60mm (distance to floor).
        A cliff means that distance suddenly increases.
        """
        return (self.left_drop_mm > baseline_mm + threshold_mm or
                self.right_drop_mm > baseline_mm + threshold_mm)

    @property
    def any_wheel_drop(self):
        return self.left_wheel_extended or self.right_wheel_extended


class SensorMonitor:
    """Background thread that polls Neato's hardware sensors.

    All sensor reads go through neato.send() which is thread-safe (has a lock).
    The main loop reads sensor state via check_and_clear() at zero cost.
    """

    def __init__(self, neato, poll_interval=0.15):
        self.neato = neato
        self.poll_interval = poll_interval
        self._state = SensorState()
        self._state_lock = threading.Lock()
        self._bumper_event = threading.Event()
        self._cliff_event = threading.Event()
        self._wheel_drop_event = threading.Event()
        self._stop_event = threading.Event()
        self._thread = None
        self._baseline_pitch = None
        self._baseline_roll = None

    def start(self):
        """Start background polling. Calibrates accelerometer baseline."""
        # Take baseline pitch/roll reading
        try:
            accel = self.neato.get_accel_parsed()
            self._baseline_pitch = accel.get('PitchInDegrees', 0.0)
            self._baseline_roll = accel.get('RollInDegrees', 0.0)
        except Exception:
            self._baseline_pitch = 0.0
            self._baseline_roll = 0.0

        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        while not self._stop_event.is_set():
            try:
                self._read_sensors()
            except Exception:
                pass  # serial hiccup, skip this cycle
            self._stop_event.wait(self.poll_interval)

    def _read_sensors(self):
        digital = self.neato.get_digital_sensors()
        analog = self.neato.get_analog_sensors()
        accel = self.neato.get_accel_parsed()

        state = SensorState(
            bumper_left_front=digital.get('LFRONTBIT', 0) == 1,
            bumper_right_front=digital.get('RFRONTBIT', 0) == 1,
            bumper_left_side=digital.get('LSIDEBIT', 0) == 1,
            bumper_right_side=digital.get('RSIDEBIT', 0) == 1,
            left_wheel_extended=digital.get('SNSR_LEFT_WHEEL_EXTENDED', 0) == 1,
            right_wheel_extended=digital.get('SNSR_RIGHT_WHEEL_EXTENDED', 0) == 1,
            on_charger=digital.get('SNSR_DC_JACK_CONNECT', 0) == 1,
            dustbin_in=digital.get('SNSR_DUSTBIN_IS_IN', 0) == 1,
            wall_distance_mm=analog.get('WallSensorInMM', 9999),
            left_drop_mm=analog.get('LeftDropInMM', 0),
            right_drop_mm=analog.get('RightDropInMM', 0),
            battery_voltage_mv=analog.get('BatteryVoltageInmV', 0),
            battery_temp_c=analog.get('BatteryTemp0InC', 0),
            current_ma=analog.get('CurrentInmA', 0),
            left_mag=analog.get('LeftMagSensor', 0),
            right_mag=analog.get('RightMagSensor', 0),
            pitch_degrees=accel.get('PitchInDegrees', 0.0),
            roll_degrees=accel.get('RollInDegrees', 0.0),
        )

        # Set events for critical conditions
        if state.any_bumper:
            self._bumper_event.set()
        if state.any_cliff():
            self._cliff_event.set()
        if state.any_wheel_drop:
            self._wheel_drop_event.set()

        with self._state_lock:
            self._state = state

    def check_and_clear(self):
        """Return current sensor state and clear bumper/cliff/wheel-drop events.

        Returns:
            tuple: (SensorState, bumper_hit: bool, cliff: bool, wheel_drop: bool)
        """
        bumper_hit = self._bumper_event.is_set()
        cliff = self._cliff_event.is_set()
        wheel_drop = self._wheel_drop_event.is_set()
        self._bumper_event.clear()
        self._cliff_event.clear()
        self._wheel_drop_event.clear()

        with self._state_lock:
            state = self._state

        return state, bumper_hit, cliff, wheel_drop

    @property
    def baseline_pitch(self):
        return self._baseline_pitch

    @property
    def baseline_roll(self):
        return self._baseline_roll

    def stop(self):
        """Stop the polling thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
