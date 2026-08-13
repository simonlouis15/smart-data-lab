"""
Device drivers for the V9 hardware, refactored for use as a bundled CLI sidecar.

These classes reimplement the exact serial protocols found in the V9-TC-EC
scripts (SelectorValvesV9.py and SyringePumpsHTPumpTCV9.py) but WITHOUT the
import-time side effects of the originals: nothing opens a serial port or moves
hardware until you explicitly construct a device and call a method. All COM
ports and serial parameters are passed in as arguments instead of being
hardcoded.

Protocol reference (unchanged from V9):

Selector valves (ASCII, terminated with \\r):
    AK          acknowledge / check connection
    AM3         set actuator to multiposition mode
    NP<count>   configure number of positions (10 for the main valve, 28 for
                the per-pump valves)
    GO<pos>     move to a position (zero-padded to 2 digits)
    CP          confirm current position

Hamilton syringe pumps (ASCII, framed as /<num><command>R\\r\\n):
    Y<size>z    set syringe size and zero the plunger
    O / I       select output / input port on the pump valve
    V<speed>    set speed
    A<pos>      move to absolute position
    P / D       relative pick / dispense
    T           stop
    F           firmware/status query (used to poll readiness)
    ?           query current absolute position
"""

import re
import time
import string

import serial


PARITY_MAP = {
    "none": serial.PARITY_NONE,
    "even": serial.PARITY_EVEN,
    "odd": serial.PARITY_ODD,
    "mark": serial.PARITY_MARK,
    "space": serial.PARITY_SPACE,
}

# Main (10-port) selector valve named modes, matching injectionmode/airmode/
# solventmode in SelectorValvesV9.py.
MAIN_VALVE_MODES = {
    "sample": 3,      # injectionmode -> GO03
    "injection": 3,
    "air": 9,         # airmode -> GO09
    "solvent": 1,     # solventmode -> GO01
}

# Fixed positions reserved on the 28-port per-pump valves (Solvent_ValveN /
# Air_ValveN in SelectorValvesV9.py).
PUMP_VALVE_PRESETS = {
    "solvent": 27,
    "air": 28,
}


def chemical_to_position(chemical: str, num_chemicals: int) -> int:
    """Map a chemical letter (A, B, C, ...) to a valve port number.

    Mirrors generate_valve_maps() in the V9 code: chemical A -> 1, B -> 2, ...
    """
    letters = string.ascii_uppercase
    if num_chemicals > len(letters):
        raise ValueError(f"num_chemicals too large, max is {len(letters)}")

    chemical = str(chemical).strip().upper()
    mapping = {chem: idx + 1 for idx, chem in enumerate(letters[:num_chemicals])}
    if chemical not in mapping:
        raise ValueError(
            f"Chemical '{chemical}' not in mapping for {num_chemicals} chemicals"
        )
    return mapping[chemical]


class SerialDevice:
    """Base class wrapping a pyserial connection with simple read/write."""

    def __init__(
        self,
        port,
        baudrate=9600,
        name="",
        bytesize=8,
        parity="none",
        stopbits=1,
        timeout=1,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
        write_timeout=1,
    ):
        self.name = name
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=PARITY_MAP[parity],
            stopbits=stopbits,
            timeout=timeout,
            xonxoff=xonxoff,
            rtscts=rtscts,
            dsrdtr=dsrdtr,
            write_timeout=write_timeout,
        )

    def write(self, command: str):
        self.ser.write(command.encode("utf-8"))
        time.sleep(0.1)

    def read(self) -> str:
        return self.ser.readline().decode("utf-8", errors="ignore").strip()

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


class SelectorValve(SerialDevice):
    """Hamilton selector valve.

    Handles both the 10-port main flow valve and the 28-port per-pump chemical
    valves; the only difference is num_positions (NP10 vs NP28).
    """

    def __init__(self, port, num_positions=10, **serial_kwargs):
        super().__init__(port, **serial_kwargs)
        self.num_positions = num_positions
        self.current_position = None

    def setup(self):
        """AK -> AM3 -> NP<count>, matching Valve_Setup()/ValveN_Setup()."""
        self.write("AK\r")
        self.read()
        self.write("AM3\r")
        self.write(f"NP{self.num_positions}\r")
        time.sleep(0.1)

    def move_to(self, position: int) -> str:
        if not 1 <= position <= self.num_positions:
            raise ValueError(
                f"Position {position} out of range 1..{self.num_positions}"
            )
        self.write(f"GO{position:02d}\r")
        self.current_position = position
        time.sleep(0.1)
        return self.confirm_position()

    def confirm_position(self) -> str:
        self.write("CP\r")
        time.sleep(0.1)
        return self.read()


class Pump(SerialDevice):
    """Hamilton syringe pump using the /<num>...R protocol.

    Primitives mirror the sample-pump functions in SyringePumpsHTPumpTCV9.py
    (PumpInitialize, PumpWithdraw, PumpInjection, PumpFullInjection,
    PumpEmpty, Debubble, position query, and cleaning).
    """

    UNITS_PER_ML = 20  # matches the int(x * 20) scaling used throughout V9
    FULL_STROKE_STEPS = 6000  # plunger steps for a full syringe stroke (A6000)

    def __init__(self, port, pump_num=1, **serial_kwargs):
        super().__init__(port, **serial_kwargs)
        self.pump_num = pump_num

    def _frame(self, command: str) -> str:
        return f"/{self.pump_num}{command}R\r\n"

    def wait_until_ready(self, max_attempts: int = 100_000):
        """Poll the 'F' status command until the pump is idle.

        Replicates the V9 PumpReady_* logic: read the raw response and inspect
        byte index 2; '@' (busy) and 'o' (moving) mean keep waiting.

        A slow move (e.g. a full-stroke withdraw) can take far longer than a
        handful of polls, so we keep waiting like the V9 `while True` loop
        rather than giving up early -- returning too soon lets the next command
        interrupt the move, which cuts a withdraw short. A blank/timed-out read
        yields an empty status and is treated as "still busy" so a dropped
        response never counts as ready.
        """
        for _ in range(max_attempts):
            self.write(self._frame("F"))
            time.sleep(0.1)
            raw = self.ser.readline()
            time.sleep(0.1)
            status = raw[2:3].decode("utf-8", errors="ignore")
            time.sleep(1)
            if status and status not in ("@", "o"):
                return status
        return None

    def send_command(self, command: str):
        self.write(self._frame(command))
        time.sleep(0.5)
        self.wait_until_ready()
        time.sleep(0.5)

    def stop(self):
        self.send_command("T")

    def initialize(
        self,
        syringe_size: int = 30,
        zero_units: int = 100,
        fill_units: int = 100,
        fill_speed: int = 6000,
    ):
        """PumpInitialize_pumpSample*: Y<size>z, OV<zero>A0, OV<fill>P<speed>."""
        self.send_command(f"Y{syringe_size}z")
        self.send_command(f"OV{zero_units}A0")
        self.send_command(f"OV{fill_units}P{fill_speed}")

    def withdraw(self, speed: int, position: int = 6000):
        """PumpWithdrawSample*: OV<speed>A<position> (default full: A6000)."""
        self.stop()
        self.send_command(f"OV{int(speed)}A{int(position)}")

    def inject(
        self,
        flow_rate: float,
        injection_time: float = 1.0,
        syringe_volume: float = 10.0,
    ):
        """Inject sample at a real flow rate, mirroring pump_flow_rate().

        Reproduces the V9 conversion done in pump_flow_rate() before it calls
        PumpInjection_pumpSample*(x1, y1):
          - plunger speed code  = flow_rate * 20            (the V value)
          - dispensed amount    = round(6000 * injection_time
                                        / (syringe_volume / flow_rate))  (the d value)
        which simplifies to (6000 steps / syringe_volume mL) * (flow_rate *
        injection_time) mL, i.e. the number of plunger steps for the volume
        delivered over injection_time.

        Args:
            flow_rate: sample flow rate in mL/min (the pre-conversion value).
            injection_time: injection duration in minutes (V9 default 1).
            syringe_volume: syringe size in mL used for the conversion
                (V9 pump_flow_rate default 10).
        """
        if flow_rate <= 0:
            raise ValueError("flow_rate must be > 0 mL/min")
        speed_code = int(flow_rate * self.UNITS_PER_ML)
        steps = round(
            self.FULL_STROKE_STEPS * injection_time / (syringe_volume / flow_rate)
        )
        self.stop()
        self.send_command(f"EV{speed_code}d{steps}")

    def inject_steps(self, speed_rate: float, steps: int):
        """Raw dispense used by routines: EV<speed_rate*20>d<steps>.

        Mirrors PumpInjection_pumpSample*(x1=speed_rate, y1=steps) directly,
        without the mL/min conversion inject() applies. Routines pass a fixed
        speed number (e.g. 20) and an explicit step count.
        """
        self.stop()
        self.send_command(f"EV{int(speed_rate * self.UNITS_PER_ML)}d{int(steps)}")

    def full_injection(self, rate: float, position: int = 0):
        """PumpFullInjection_pumpSample*: EV<rate*20>A<position>."""
        self.stop()
        self.send_command(f"EV{int(rate * self.UNITS_PER_ML)}A{int(position)}")

    def empty(self, rate: float):
        """PumpEmpty_PumpSample*: IV<rate*20>A0."""
        self.stop()
        self.send_command(f"IV{int(rate * self.UNITS_PER_ML)}A0")

    def debubble(self, rate: float, duration: int):
        """Debubble_pumpSample*: IV<rate*20>d<duration>."""
        self.stop()
        self.send_command(f"IV{int(rate * self.UNITS_PER_ML)}d{int(duration)}")

    def query_position(self):
        """Position_SamplePump*: send '?', parse the `<number> response."""
        self.write(self._frame("?"))
        time.sleep(0.1)
        raw = self.ser.readline().decode("utf-8", errors="ignore")
        match = re.search(r"`(\d+)", raw)
        return int(match.group(1)) if match else None

    def clean(self, flush_rate: float = 10, withdraw_speed: int = 300, withdraw_position: int = 6000):
        """Standalone syringe clean (empty -> withdraw -> empty).

        This is the pump-only portion of PumpCleaning_pumpSample*_aut /
        PumpCleaning_JarSwitch*; valve coordination (solvent/air/chemical) is
        orchestrated by the caller. `withdraw_position` defaults to a full
        stroke (6000) but jar-switch cleaning uses a partial fill.
        """
        self.empty(flush_rate)
        self.wait_until_ready()
        self.withdraw(withdraw_speed, withdraw_position)
        self.wait_until_ready()
        self.empty(flush_rate)


# ---------------------------------------------------------------------------
# Config -> device builders
#
# Accept a device config dict using the same keys as backend/config/config.json
# (e.g. "Port", "Baudrate", "Pump Number", "Positions") and construct a device.
# Used by the `routine` subcommand, which receives whole configs as JSON.
# ---------------------------------------------------------------------------

def _serial_kwargs_from_config(cfg: dict) -> dict:
    return dict(
        port=cfg["Port"],
        baudrate=int(cfg.get("Baudrate", 9600)),
        name=cfg.get("Name", ""),
        bytesize=int(cfg.get("Bytesize", 8)),
        parity=cfg.get("Parity", "none"),
        stopbits=float(cfg.get("Stopbits", 1)),
        timeout=float(cfg.get("Timeout", 1)),
        xonxoff=bool(cfg.get("Xonxoff", False)),
        rtscts=bool(cfg.get("Rtscts", False)),
        dsrdtr=bool(cfg.get("Dsrdtr", False)),
        write_timeout=float(cfg.get("WriteTimeout", 1)),
    )


def pump_from_config(cfg: dict) -> Pump:
    kwargs = _serial_kwargs_from_config(cfg)
    return Pump(pump_num=int(cfg.get("Pump Number", 1)), **kwargs)


def valve_from_config(cfg: dict) -> SelectorValve:
    kwargs = _serial_kwargs_from_config(cfg)
    return SelectorValve(num_positions=int(cfg.get("Positions", 10)), **kwargs)
