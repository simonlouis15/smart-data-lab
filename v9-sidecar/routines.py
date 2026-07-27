"""High-level pump + valve routines ported from the V9-TC-EC code.

Each routine holds one or more open serial connections and interleaves valve
and pump commands with the exact ordering, sleeps, and (where relevant)
threading used in V9. Keeping them in the sidecar preserves the validated
timing and lets a routine drive a device over a single persistent connection
instead of re-opening the port for every step.

Ported from:
  - switch_sampleN_aut()  (SampleSwitchV9.py)   -> switch_sample()
  - Switch_Jar_PumpN() / JarSwitchCombined()    -> jar_switch()
  - pump_flow_rate()      (SyringePumpsHTPumpTCV9.py) -> flow_rate()
"""

import threading
import time

from devices import (
    MAIN_VALVE_MODES,
    PUMP_VALVE_PRESETS,
    Pump,
    SelectorValve,
    chemical_to_position,
)


def switch_sample(pump: Pump, valve: SelectorValve):
    """Automated line switch/clean for one sample pump + its 28-port valve.

    Port of switch_sampleN_aut(): empty the syringe, clean it against the
    solvent then air ports, then prime/flush the line by alternating
    solvent/air withdraw+inject cycles.
    """
    solvent = PUMP_VALVE_PRESETS["solvent"]  # GO27
    air = PUMP_VALVE_PRESETS["air"]          # GO28

    valve.setup()

    pump.empty(10)
    time.sleep(1)
    valve.move_to(solvent)
    time.sleep(1)
    pump.clean(flush_rate=10, withdraw_speed=300)      # solvent clean
    time.sleep(1)
    valve.move_to(air)
    time.sleep(1)
    pump.clean(flush_rate=10, withdraw_speed=300)      # air clean
    time.sleep(1)
    pump.clean(flush_rate=10, withdraw_speed=300)      # air clean (2nd pass)
    time.sleep(1)

    # Line cleaning: alternate solvent/air, withdraw then dispense.
    valve.move_to(solvent)
    time.sleep(1)
    pump.withdraw(300, 6000)
    time.sleep(1)
    pump.inject_steps(20, 6000)
    time.sleep(1)

    valve.move_to(air)
    pump.withdraw(300, 6000)
    time.sleep(1)
    pump.inject_steps(20, 6000)
    time.sleep(1)
    pump.withdraw(300, 6000)
    time.sleep(1)
    pump.inject_steps(20, 6000)
    time.sleep(1)


def jar_switch(
    pump: Pump,
    valve: SelectorValve,
    chemical: str,
    num_chemicals: int,
    cycles: int = 3,
):
    """Route a pump's 28-port valve to a chemical port and prime the line.

    Based on Switch_Jar_PumpN() / JarSwitchCombined(): empty the syringe, open
    the valve to the requested chemical, then run partial-fill clean cycles
    (PumpCleaning_JarSwitch*, withdraw to 3000) to prime the line with the new
    chemical.
    """
    position = chemical_to_position(chemical, num_chemicals)

    valve.setup()

    pump.empty(10)
    time.sleep(1)
    valve.move_to(position)
    time.sleep(1)
    for _ in range(cycles):
        pump.clean(flush_rate=10, withdraw_speed=300, withdraw_position=3000)
        time.sleep(1)


def flow_rate(
    main_valve: SelectorValve,
    pump_rates,
    injection_time: float = 1.0,
    syringe_volume: float = 10.0,
):
    """Concurrent multi-pump dosing at real mL/min rates through the main valve.

    Port of pump_flow_rate(): switch the main valve to injection/sample mode,
    debubble every active pump simultaneously, then inject every active pump
    simultaneously. The per-pump step count matches V9 exactly:

        steps = round(6000 * injection_time / (syringe_volume / rate))

    Args:
        main_valve: the 10-port main flow valve.
        pump_rates: iterable of (Pump, rate_ml_min) tuples. Pumps with a
            rate <= 0 are skipped.
    """
    active = [(p, float(r)) for (p, r) in pump_rates if r and float(r) > 0]

    main_valve.setup()
    main_valve.move_to(MAIN_VALVE_MODES["sample"])  # injectionmode -> GO03
    time.sleep(5)

    if not active:
        return

    # Debubble all active pumps concurrently (IV100d0 == debubble(5, 0)).
    debubble_threads = [
        threading.Thread(target=p.debubble, args=(5, 0)) for (p, _) in active
    ]
    for t in debubble_threads:
        t.start()
    for t in debubble_threads:
        t.join()

    time.sleep(0.1)

    # Inject all active pumps concurrently at their individual flow rates.
    def _inject(pump: Pump, rate: float):
        steps = round(6000 * injection_time / (syringe_volume / rate))
        pump.inject_steps(rate, steps)

    inject_threads = [
        threading.Thread(target=_inject, args=(p, r)) for (p, r) in active
    ]
    for t in inject_threads:
        t.start()
    for t in inject_threads:
        t.join()
