"""Tests for the multi-device routines in ``routines.py``.

Routines interleave valve moves and pump commands (some concurrently via
threads). With the serial port faked and sleeps neutralised, these run
instantly and let us assert the key ordering/frames without a rig.
"""

from devices import Pump, SelectorValve
import routines


def _sent(device):
    return [w for w in device.ser.written if not w.endswith("FR\r\n")]


def test_switch_sample_cleans_solvent_then_air(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    valve = SelectorValve(port="COM3", num_positions=28)

    routines.switch_sample(pump, valve)

    valve_frames = valve.ser.written
    # Valve set up as a 28-port valve and visits solvent (27) then air (28).
    assert "NP28\r" in valve_frames
    assert "GO27\r" in valve_frames  # solvent
    assert "GO28\r" in valve_frames  # air
    # solvent move happens before the air move.
    assert valve_frames.index("GO27\r") < valve_frames.index("GO28\r")

    # The routine starts by emptying the syringe (IV200A0 == empty(10)).
    assert "/1IV200A0R\r\n" in _sent(pump)


def test_jar_switch_routes_to_chemical_and_primes(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    valve = SelectorValve(port="COM3", num_positions=28)

    routines.jar_switch(pump, valve, chemical="C", num_chemicals=26, cycles=3)

    # Chemical C -> port 3.
    assert "GO03\r" in valve.ser.written

    # cycles=3 partial-fill cleans; each clean does one withdraw to 3000.
    withdraws = [c for c in _sent(pump) if c == "/1OV300A3000R\r\n"]
    assert len(withdraws) == 3


def test_jar_switch_respects_cycle_count(fake_serial):
    pump = Pump(port="COM10", pump_num=1)
    valve = SelectorValve(port="COM3", num_positions=28)

    routines.jar_switch(pump, valve, chemical="A", num_chemicals=26, cycles=1)

    withdraws = [c for c in _sent(pump) if c == "/1OV300A3000R\r\n"]
    assert len(withdraws) == 1


def test_flow_rate_switches_main_valve_and_injects(fake_serial):
    main_valve = SelectorValve(port="COM9", num_positions=10)
    pump1 = Pump(port="COM10", pump_num=1)
    pump2 = Pump(port="COM7", pump_num=1)

    routines.flow_rate(
        main_valve,
        [(pump1, 0.3), (pump2, 0.2)],
        injection_time=1.0,
        syringe_volume=10.0,
    )

    # Main valve switched to injection/sample mode (position 3).
    assert "GO03\r" in main_valve.ser.written

    # pump1: steps = round(6000 * 1 / (10 / 0.3)) = 180; speed = int(0.3*20)=6.
    assert "/1EV6d180R\r\n" in _sent(pump1)
    # pump2: steps = round(6000 * 1 / (10 / 0.2)) = 120; speed = int(0.2*20)=4.
    assert "/1EV4d120R\r\n" in _sent(pump2)


def test_flow_rate_skips_zero_rate_pumps(fake_serial):
    main_valve = SelectorValve(port="COM9", num_positions=10)
    active = Pump(port="COM10", pump_num=1)
    idle = Pump(port="COM7", pump_num=1)

    routines.flow_rate(main_valve, [(active, 0.3), (idle, 0)])

    # The active pump injects; the zero-rate pump issues no EV inject frame.
    assert any(c.startswith("/1EV") for c in _sent(active))
    assert not any(c.startswith("/1EV") for c in _sent(idle))


def test_flow_rate_no_active_pumps_only_moves_valve(fake_serial):
    main_valve = SelectorValve(port="COM9", num_positions=10)
    pump = Pump(port="COM10", pump_num=1)

    routines.flow_rate(main_valve, [(pump, 0)])

    assert "GO03\r" in main_valve.ser.written
    # No inject frames when nothing is active.
    assert not any(c.startswith("/1EV") for c in _sent(pump))
