"""End-to-end tests for the CLI in ``cli.py``.

These drive ``cli.main(argv)`` exactly like the Tauri sidecar would, but with
the serial port faked. They cover argument parsing, the clean-error validation
paths documented in ``test_commands.txt`` section 4, and that the right V9
frames reach the (fake) device.
"""

import json

import pytest

import cli


def _last_device(fake_serial):
    """The most recently opened fake device (routines open several)."""
    return fake_serial.instances[-1]


def _first_device(fake_serial):
    return fake_serial.instances[0]


def _sent(device):
    return [w for w in device.written if not w.endswith("FR\r\n")]


# ---------------------------------------------------------------------------
# valve subcommand
# ---------------------------------------------------------------------------

def test_cli_valve_mode(fake_serial):
    cli.main(["valve", "--port", "COM9", "--positions", "10", "--mode", "solvent"])
    valve = _first_device(fake_serial)
    assert "NP10\r" in valve.written
    assert "GO01\r" in valve.written


def test_cli_valve_preset(fake_serial):
    cli.main(["valve", "--port", "COM3", "--positions", "28", "--preset", "air"])
    valve = _first_device(fake_serial)
    assert "GO28\r" in valve.written


def test_cli_valve_chemical(fake_serial):
    cli.main(
        [
            "valve", "--port", "COM3", "--positions", "28",
            "--chemical", "C", "--num-chemicals", "26",
        ]
    )
    valve = _first_device(fake_serial)
    assert "GO03\r" in valve.written


def test_cli_valve_raw_position(fake_serial):
    cli.main(["valve", "--port", "COM3", "--positions", "28", "--position", "14"])
    valve = _first_device(fake_serial)
    assert "GO14\r" in valve.written


def test_cli_valve_chemical_requires_num_chemicals(fake_serial):
    with pytest.raises(SystemExit):
        cli.main(["valve", "--port", "COM3", "--positions", "28", "--chemical", "A"])


def test_cli_valve_requires_an_action(fake_serial):
    # The mutually-exclusive action group is required by argparse.
    with pytest.raises(SystemExit):
        cli.main(["valve", "--port", "COM9", "--positions", "10"])


# ---------------------------------------------------------------------------
# pump subcommand
# ---------------------------------------------------------------------------

def test_cli_pump_initialize(fake_serial):
    cli.main(["pump", "--port", "COM10", "--pump-num", "1", "--option", "initialize"])
    pump = _first_device(fake_serial)
    assert "/1Y30zR\r\n" in _sent(pump)


def test_cli_pump_inject(fake_serial):
    cli.main(
        ["pump", "--port", "COM10", "--pump-num", "1", "--option", "inject", "--rate", "0.3"]
    )
    pump = _first_device(fake_serial)
    assert "/1EV6d180R\r\n" in _sent(pump)


def test_cli_pump_withdraw_requires_speed(fake_serial):
    # Documented section-4 sanity check: missing --speed exits cleanly.
    with pytest.raises(SystemExit):
        cli.main(["pump", "--port", "COM10", "--option", "withdraw"])


def test_cli_pump_empty_requires_rate(fake_serial):
    with pytest.raises(SystemExit):
        cli.main(["pump", "--port", "COM10", "--option", "empty"])


def test_cli_pump_stop(fake_serial):
    cli.main(["pump", "--port", "COM10", "--pump-num", "1", "--option", "stop"])
    pump = _first_device(fake_serial)
    assert "/1TR\r\n" in _sent(pump)


# ---------------------------------------------------------------------------
# routine subcommand
# ---------------------------------------------------------------------------

def test_cli_routine_switch_sample(fake_serial):
    payload = json.dumps(
        {
            "pump": {"Port": "COM10", "Pump Number": 1},
            "valve": {"Port": "COM3", "Positions": 28},
        }
    )
    cli.main(["routine", "--routine", "switch-sample", "--payload", payload])

    all_writes = [w for dev in fake_serial.instances for w in dev.written]
    assert "GO27\r" in all_writes  # solvent
    assert "GO28\r" in all_writes  # air


def test_cli_routine_flow_rate(fake_serial):
    payload = json.dumps(
        {
            "main_valve": {"Port": "COM9", "Positions": 10},
            "pumps": [{"config": {"Port": "COM10", "Pump Number": 1}, "rate": 0.3}],
        }
    )
    cli.main(["routine", "--routine", "flow-rate", "--payload", payload])

    all_writes = [w for dev in fake_serial.instances for w in dev.written]
    assert "GO03\r" in all_writes            # main valve -> injection
    assert "/1EV6d180R\r\n" in all_writes    # pump inject


def test_cli_routine_invalid_json(fake_serial):
    with pytest.raises(SystemExit):
        cli.main(["routine", "--routine", "switch-sample", "--payload", "not json"])


def test_cli_routine_missing_payload_key(fake_serial):
    with pytest.raises(SystemExit):
        cli.main(["routine", "--routine", "switch-sample", "--payload", "{}"])


def test_cli_routine_unknown_name_rejected_by_argparse(fake_serial):
    with pytest.raises(SystemExit):
        cli.main(["routine", "--routine", "does-not-exist", "--payload", "{}"])


# ---------------------------------------------------------------------------
# top-level parser
# ---------------------------------------------------------------------------

def test_cli_requires_subcommand(fake_serial):
    with pytest.raises(SystemExit):
        cli.main([])
