"""Unit tests for the device drivers in ``devices.py``.

Each test constructs a driver directly (the ``fake_serial`` fixture has already
replaced the real serial port) and asserts on the exact V9 protocol frames the
driver writes. This verifies the protocol translation that used to require the
physical rig.
"""

import pytest

from devices import (
    MAIN_VALVE_MODES,
    PUMP_VALVE_PRESETS,
    Pump,
    SelectorValve,
    chemical_to_position,
    pump_from_config,
    valve_from_config,
)


# ---------------------------------------------------------------------------
# chemical_to_position mapping (pure logic, no serial)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("chemical", "num", "expected"),
    [
        ("A", 26, 1),
        ("C", 26, 3),
        ("a", 26, 1),   # case-insensitive
        (" b ", 26, 2),  # whitespace tolerant
        ("Z", 26, 26),
    ],
)
def test_chemical_to_position_valid(chemical, num, expected):
    assert chemical_to_position(chemical, num) == expected


def test_chemical_to_position_out_of_campaign():
    # Only 3 chemicals in the campaign, so 'D' has no port.
    with pytest.raises(ValueError):
        chemical_to_position("D", 3)


def test_chemical_to_position_too_many_chemicals():
    with pytest.raises(ValueError):
        chemical_to_position("A", 27)


# ---------------------------------------------------------------------------
# SelectorValve
# ---------------------------------------------------------------------------

def test_valve_setup_sends_ak_am3_np(fake_serial):
    valve = SelectorValve(port="COM9", num_positions=10)
    valve.setup()
    assert valve.ser.written == ["AK\r", "AM3\r", "NP10\r"]


def test_valve_setup_28_positions(fake_serial):
    valve = SelectorValve(port="COM3", num_positions=28)
    valve.setup()
    assert "NP28\r" in valve.ser.written


@pytest.mark.parametrize(
    ("mode", "frame"),
    [
        ("solvent", "GO01\r"),   # position 1
        ("sample", "GO03\r"),    # injectionmode -> position 3
        ("injection", "GO03\r"),
        ("air", "GO09\r"),       # position 9
    ],
)
def test_valve_main_modes(fake_serial, mode, frame):
    valve = SelectorValve(port="COM9", num_positions=10)
    valve.move_to(MAIN_VALVE_MODES[mode])
    assert frame in valve.ser.written
    # move_to always confirms afterwards.
    assert "CP\r" in valve.ser.written


@pytest.mark.parametrize(
    ("preset", "frame"),
    [
        ("solvent", "GO27\r"),
        ("air", "GO28\r"),
    ],
)
def test_valve_pump_presets(fake_serial, preset, frame):
    valve = SelectorValve(port="COM3", num_positions=28)
    valve.move_to(PUMP_VALVE_PRESETS[preset])
    assert frame in valve.ser.written


def test_valve_chemical_routing(fake_serial):
    valve = SelectorValve(port="COM3", num_positions=28)
    valve.move_to(chemical_to_position("C", 26))  # C -> port 3
    assert "GO03\r" in valve.ser.written


def test_valve_position_out_of_range(fake_serial):
    valve = SelectorValve(port="COM9", num_positions=10)
    with pytest.raises(ValueError):
        valve.move_to(11)
    with pytest.raises(ValueError):
        valve.move_to(0)


def test_valve_confirm_position_reads_reply(fake_serial):
    valve = SelectorValve(port="COM9", num_positions=10)
    valve.ser.queue_response("GO03OK\r\n")
    assert valve.move_to(3) == "GO03OK"


# ---------------------------------------------------------------------------
# Pump
# ---------------------------------------------------------------------------

def _sent(pump):
    """Pump frames excluding the readiness-poll ('F') frames."""
    return [w for w in pump.ser.written if not w.endswith("FR\r\n")]


def test_pump_frame_format(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    assert pump._frame("T") == "/1TR\r\n"
    pump2 = Pump(port="COM7", pump_num=2)
    assert pump2._frame("Y30z") == "/2Y30zR\r\n"


def test_pump_initialize(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    pump.initialize(syringe_size=30)
    sent = _sent(pump)
    assert sent == ["/1Y30zR\r\n", "/1OV100A0R\r\n", "/1OV100P6000R\r\n"]


def test_pump_withdraw_stops_first(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    pump.withdraw(speed=300, position=6000)
    sent = _sent(pump)
    assert sent == ["/1TR\r\n", "/1OV300A6000R\r\n"]


def test_pump_inject_converts_flow_rate(fake_serial):
    # rate 0.3 mL/min -> speed code int(0.3*20)=6;
    # steps = round(6000 * 1 / (10 / 0.3)) = 180.
    pump = Pump(port="COM10", pump_num=1)
    pump.inject(0.3, injection_time=1.0, syringe_volume=10.0)
    assert "/1EV6d180R\r\n" in _sent(pump)


def test_pump_inject_rejects_nonpositive_rate(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    with pytest.raises(ValueError):
        pump.inject(0)


def test_pump_full_injection(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    pump.full_injection(10, position=0)
    assert "/1EV200A0R\r\n" in _sent(pump)


def test_pump_empty(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    pump.empty(10)
    assert "/1IV200A0R\r\n" in _sent(pump)


def test_pump_debubble(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    pump.debubble(5, 6000)
    assert "/1IV100d6000R\r\n" in _sent(pump)


def test_pump_stop(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    pump.stop()
    assert "/1TR\r\n" in _sent(pump)


def test_pump_clean_sequence(fake_serial):
    # clean() = empty -> withdraw -> empty; empty() and withdraw() each stop
    # (send 'T') before their action.
    pump = Pump(port="COM10", pump_num=1)
    pump.clean(flush_rate=10, withdraw_speed=300)
    sent = _sent(pump)
    assert sent == [
        "/1TR\r\n",             # empty stops first
        "/1IV200A0R\r\n",       # empty
        "/1TR\r\n",             # withdraw stops first
        "/1OV300A6000R\r\n",    # withdraw
        "/1TR\r\n",             # empty stops first
        "/1IV200A0R\r\n",       # empty
    ]


def test_pump_query_position_parses_reply(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    pump.ser.queue_response("/0`1234\r\n")
    assert pump.query_position() == 1234


def test_pump_query_position_no_match_returns_none(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    pump.ser.queue_response("garbage\r\n")
    assert pump.query_position() is None


def test_pump_wait_until_ready_returns_when_idle(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    # default response byte[2] is '`' (idle), so this returns immediately.
    assert pump.wait_until_ready() not in ("@", "o")


# ---------------------------------------------------------------------------
# config -> device builders
# ---------------------------------------------------------------------------

def test_pump_from_config(fake_serial):
    cfg = {"Port": "COM10", "Pump Number": 2, "Baudrate": 9600}
    pump = pump_from_config(cfg)
    assert isinstance(pump, Pump)
    assert pump.pump_num == 2
    assert pump.ser.port == "COM10"


def test_valve_from_config(fake_serial):
    cfg = {"Port": "COM3", "Positions": 28}
    valve = valve_from_config(cfg)
    assert isinstance(valve, SelectorValve)
    assert valve.num_positions == 28
    assert valve.ser.port == "COM3"
