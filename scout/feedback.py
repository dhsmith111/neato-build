"""Diagnostic feedback via Neato LEDs and sounds."""

from scout.rules import ActionType


class Feedback:
    """Real-time LED and sound feedback for diagnostic mode.

    LED signals (start button):
      Green steady  = path clear, driving normally
      Green blink   = obstacle detected, slowing down
      Amber steady  = close obstacle or pet, stopped/waiting
      Amber blink   = backing up or turning
      Red           = cliff or emergency stop

    Sound signals (per safety layer):
      Layer 1 (hardware): Sound 19 (Alert) — bumper/cliff/wall
      Layer 2 (vision):   Sound 3 (Attention) — pet/obstacle
      Layer 3 (LiDAR):    Sound 11 (Exploring) — scan complete
      Picked up:          Sound 13
    """

    def __init__(self, neato, config):
        self.neato = neato
        self.enabled = config.get("diag_mode", False)
        self.sounds = config.get("sounds", {})
        self._last_led = None
        self._last_action_type = None

    def signal(self, action, bumper_hit=False, cliff=False, wheel_drop=False):
        """Update LED and optionally play sound based on current action."""
        if not self.enabled:
            return

        at = action.action_type

        # --- Sounds (one-shot per event) ---
        if cliff:
            self._play("layer1_alert")
        elif wheel_drop:
            self._play("picked_up")
        elif bumper_hit:
            self._play("layer1_alert")
        elif at == ActionType.WAIT:
            self._play("layer2_attention")
        elif at in (ActionType.BACKUP, ActionType.TURN_LEFT, ActionType.TURN_RIGHT):
            # Vision-triggered avoidance maneuver
            if at != self._last_action_type:
                self._play("layer2_attention")
        elif at == ActionType.SLOW_FORWARD:
            if self._last_action_type != ActionType.SLOW_FORWARD:
                self._play("layer3_exploring")

        self._last_action_type = at

        # --- LEDs ---
        if cliff or wheel_drop:
            self._set_led("LEDRed")
        elif at == ActionType.STOP:
            self._set_led("ButtonAmber")
        elif at == ActionType.WAIT:
            self._set_led("ButtonAmber")
        elif at in (ActionType.BACKUP, ActionType.TURN_LEFT, ActionType.TURN_RIGHT):
            self._set_led("ButtonAmber", blink=True)
        elif at == ActionType.SLOW_FORWARD:
            self._set_led("ButtonGreen", blink=True)
        elif at == ActionType.FORWARD:
            self._set_led("ButtonGreen")

    def startup(self):
        """Play startup sound and set green LED."""
        if not self.enabled:
            return
        self._play("startup")
        self._set_led("ButtonGreen")

    def shutdown(self):
        """Play shutdown sound and turn off LED."""
        if not self.enabled:
            return
        self._play("shutdown")
        try:
            self.neato.set_led("ButtonOff")
        except Exception:
            pass

    def _play(self, sound_key):
        """Play a sound by config key name."""
        sound_id = self.sounds.get(sound_key)
        if sound_id is not None:
            try:
                self.neato.play_sound(sound_id)
            except Exception:
                pass

    def _set_led(self, led_name, blink=False):
        """Set LED state, avoiding redundant serial calls."""
        key = (led_name, blink)
        if key == self._last_led:
            return
        self._last_led = key
        try:
            if blink:
                self.neato.set_led(led_name, "BlinkOn")
            else:
                self.neato.set_led("BlinkOff", led_name)
        except Exception:
            pass
