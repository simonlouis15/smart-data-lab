"""
V9 hardware control CLI.

A thin, side-effect-free command-line wrapper around the V9 pump and selector
valve drivers (see devices.py). It is designed to be bundled into a single
executable (e.g. with PyInstaller) and invoked as a Tauri sidecar, one process
per action, exactly like the original backend/main.py.

Examples
--------
Main 10-port valve to solvent mode:
    python cli.py valve --port COM9 --positions 10 --mode solvent

28-port valve: route chemical C (out of 26) on pump 1's valve:
    python cli.py valve --port COM3 --positions 28 --chemical C --num-chemicals 26

28-port valve to its reserved solvent port (27):
    python cli.py valve --port COM3 --positions 28 --preset solvent

Initialize a sample pump:
    python cli.py pump --port COM10 --pump-num 1 --option initialize

Inject at 0.3 mL/min for a given duration:
    python cli.py pump --port COM10 --option inject --rate 0.3 --duration 6000

Run a multi-device routine (device configs are passed as a JSON payload):
    python cli.py routine --routine switch-sample --payload "{\"pump\": {...}, \"valve\": {...}}"
"""

import sys
import json
import argparse

from loguru import logger

import routines
from devices import (
    SelectorValve,
    Pump,
    MAIN_VALVE_MODES,
    PUMP_VALVE_PRESETS,
    chemical_to_position,
    pump_from_config,
    valve_from_config,
)


def str2bool(value) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def add_serial_args(parser: argparse.ArgumentParser):
    """Shared serial-connection options for every subcommand."""
    parser.add_argument("--name", required=False, default="")
    parser.add_argument("--port", required=True)
    parser.add_argument("--baudrate", type=int, default=9600)
    parser.add_argument("--bytesize", type=int, default=8)
    parser.add_argument(
        "--parity", default="none",
        choices=["none", "even", "odd", "mark", "space"],
    )
    parser.add_argument("--stopbits", type=float, default=1)
    parser.add_argument("--timeout", type=float, default=1)
    parser.add_argument("--xonxoff", default="false")
    parser.add_argument("--rtscts", default="false")
    parser.add_argument("--dsrdtr", default="false")
    parser.add_argument("--write-timeout", type=float, default=1)


def serial_kwargs(args) -> dict:
    return dict(
        baudrate=args.baudrate,
        name=args.name,
        bytesize=args.bytesize,
        parity=args.parity,
        stopbits=args.stopbits,
        timeout=args.timeout,
        xonxoff=str2bool(args.xonxoff),
        rtscts=str2bool(args.rtscts),
        dsrdtr=str2bool(args.dsrdtr),
        write_timeout=args.write_timeout,
    )


def valve_controls(args):
    logger.info(f"Valve on {args.port} ({args.positions} positions)")

    valve = SelectorValve(
        port=args.port,
        num_positions=args.positions,
        **serial_kwargs(args),
    )

    try:
        valve.setup()

        if args.mode is not None:
            position = MAIN_VALVE_MODES[args.mode]
            logger.info(f"Mode '{args.mode}' -> position {position}")
        elif args.preset is not None:
            position = PUMP_VALVE_PRESETS[args.preset]
            logger.info(f"Preset '{args.preset}' -> position {position}")
        elif args.chemical is not None:
            if args.num_chemicals is None:
                raise SystemExit("--chemical requires --num-chemicals")
            position = chemical_to_position(args.chemical, args.num_chemicals)
            logger.info(f"Chemical '{args.chemical}' -> position {position}")
        else:
            position = args.position

        response = valve.move_to(position)
        logger.info(f"Confirmed position: {response}")
    finally:
        valve.close()


def pump_controls(args):
    logger.info(f"Pump {args.pump_num} on {args.port}, option '{args.option}'")

    pump = Pump(
        port=args.port,
        pump_num=args.pump_num,
        **serial_kwargs(args),
    )

    def require(value, flag):
        if value is None:
            raise SystemExit(f"--{flag} is required for option '{args.option}'")
        return value

    try:
        pump.wait_until_ready()

        if args.option == "initialize":
            pump.initialize(syringe_size=args.syringe_size)
        elif args.option == "withdraw":
            pump.withdraw(require(args.speed, "speed"), position=args.position or 6000)
        elif args.option == "inject":
            pump.inject(
                require(args.rate, "rate"),
                injection_time=args.injection_time,
                syringe_volume=args.syringe_volume,
            )
        elif args.option == "full-injection":
            pump.full_injection(require(args.rate, "rate"), position=args.position or 0)
        elif args.option == "empty":
            pump.empty(require(args.rate, "rate"))
        elif args.option == "debubble":
            pump.debubble(require(args.rate, "rate"), require(args.duration, "duration"))
        elif args.option == "clean":
            pump.clean(flush_rate=args.rate or 10, withdraw_speed=args.speed or 300)
        elif args.option == "stop":
            pump.stop()
        elif args.option == "query-position":
            logger.info(f"Current position: {pump.query_position()}")
    finally:
        pump.close()


def routine_controls(args):
    """Run a multi-device pump/valve routine described by a JSON payload.

    The payload carries whole device configs (same keys as
    backend/config/config.json), so a routine can open the connections it
    needs and drive them over persistent ports with V9 timing.
    """
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as e:
        raise SystemExit(f"--payload is not valid JSON: {e}")

    logger.info(f"Routine '{args.routine}'")
    opened = []

    def track(device):
        opened.append(device)
        return device

    try:
        if args.routine == "switch-sample":
            pump = track(pump_from_config(payload["pump"]))
            valve = track(valve_from_config(payload["valve"]))
            routines.switch_sample(pump, valve)

        elif args.routine == "jar-switch":
            pump = track(pump_from_config(payload["pump"]))
            valve = track(valve_from_config(payload["valve"]))
            routines.jar_switch(
                pump,
                valve,
                chemical=payload["chemical"],
                num_chemicals=int(payload["num_chemicals"]),
                cycles=int(payload.get("cycles", 3)),
            )

        elif args.routine == "flow-rate":
            main_valve = track(valve_from_config(payload["main_valve"]))
            pump_rates = [
                (track(pump_from_config(item["config"])), float(item["rate"]))
                for item in payload["pumps"]
            ]
            routines.flow_rate(
                main_valve,
                pump_rates,
                injection_time=float(payload.get("injection_time", 1.0)),
                syringe_volume=float(payload.get("syringe_volume", 10.0)),
            )
        else:
            raise SystemExit(f"Unknown routine '{args.routine}'")

        logger.info(f"Routine '{args.routine}' complete")
    except KeyError as e:
        raise SystemExit(f"Routine '{args.routine}' payload missing key: {e}")
    finally:
        for device in opened:
            device.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V9 hardware control CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # ---- valve ----
    valve = subparsers.add_parser("valve", help="Selector valve controls")
    add_serial_args(valve)
    valve.add_argument(
        "--positions", type=int, default=10,
        help="Number of valve positions (10 for main valve, 28 for pump valves)",
    )
    action = valve.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--mode", choices=sorted(MAIN_VALVE_MODES.keys()),
        help="Named mode for the 10-port main valve",
    )
    action.add_argument(
        "--preset", choices=sorted(PUMP_VALVE_PRESETS.keys()),
        help="Reserved port on a 28-port pump valve (solvent=27, air=28)",
    )
    action.add_argument(
        "--chemical",
        help="Chemical letter to route on a 28-port valve (requires --num-chemicals)",
    )
    action.add_argument("--position", type=int, help="Move to a raw position number")
    valve.add_argument(
        "--num-chemicals", type=int, default=None,
        help="Total chemicals in the campaign (for --chemical mapping)",
    )
    valve.set_defaults(func=valve_controls)

    # ---- pump ----
    pump = subparsers.add_parser("pump", help="Syringe pump controls")
    add_serial_args(pump)
    pump.add_argument("--pump-num", type=int, default=1)
    pump.add_argument(
        "--option", required=True,
        choices=[
            "initialize", "withdraw", "inject", "full-injection",
            "empty", "debubble", "clean", "stop", "query-position",
        ],
    )
    pump.add_argument("--rate", type=float, default=None, help="Flow rate in mL/min (inject)")
    pump.add_argument("--speed", type=int, default=None, help="Withdraw speed code")
    pump.add_argument("--position", type=int, default=None, help="Absolute position")
    pump.add_argument("--duration", type=int, default=None, help="Dispense step count (d) for debubble")
    pump.add_argument(
        "--injection-time", type=float, default=1.0,
        help="Injection duration in minutes for inject (V9 default 1)",
    )
    pump.add_argument(
        "--syringe-volume", type=float, default=10.0,
        help="Syringe volume in mL used for inject flow-rate conversion (V9 default 10)",
    )
    pump.add_argument("--syringe-size", type=int, default=30, help="Syringe size for initialize")
    pump.set_defaults(func=pump_controls)

    # ---- routine ----
    routine = subparsers.add_parser(
        "routine", help="Multi-step pump/valve routines ported from V9"
    )
    routine.add_argument(
        "--routine", required=True,
        choices=["switch-sample", "jar-switch", "flow-rate"],
        help="Which routine to run",
    )
    routine.add_argument(
        "--payload", required=True,
        help="JSON payload with device configs and routine parameters",
    )
    routine.set_defaults(func=routine_controls)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)
