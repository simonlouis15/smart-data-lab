#!/usr/bin/env python3

import argparse

from SelectorValvesV9 import (
    Valve_Setup,
    Valve1_Setup,
    Valve2_Setup,
    Valve3_Setup,
    injectionmode,
    airmode,
    solventmode,
    open_valve1,
    open_valve2,
    open_valve3,
    Solvent_Valve1,
    Solvent_Valve2,
    Solvent_Valve3,
    Air_Valve1,
    Air_Valve2,
    Air_Valve3,
)

from ChemicalAssignmentV9 import (
    generate_valve_maps,
    assign_chemicals,
)

from CleaningV9 import (
    cleaning_part1,
    Cleaning_part2,
    Cleaning_part2_switch,
    cleanCp,
    airpurge,
)

from SyringePumpsHTPumpTCV9 import (
    # Sample 1
    PumpInitialize_pumpSample1,
    PumpWithdrawSample1,
    PumpWithdrawSample1_Volume1,
    PumpInjection_pumpSample1,
    PumpFullInjection_pumpSample1,
    PumpEmpty_PumpSample1,
    Debubble_pumpSample1,

    # Sample 2
    PumpInitialize_pumpSample2,
    PumpWithdrawSample2,
    PumpWithdrawSample2_Volume2,
    PumpInjection_pumpSample2,
    PumpFullInjection_pumpSample2,
    PumpEmpty_PumpSample2,
    Debubble_pumpSample2,

    # Sample 3
    PumpInitialize_pumpSample3,
    PumpWithdrawSample3,
    PumpWithdrawSample3_Volume3,
    PumpInjection_pumpSample3,
    PumpFullInjection_pumpSample3,
    PumpEmpty_PumpSample3,
    Debubble_pumpSample3,
)

###########################################################################
# Helpers
###########################################################################

def get_maps(num_chems):
    return generate_valve_maps(num_chems)


###########################################################################
# Selector Valve
###########################################################################

def selector_initialize(_):
    Valve_Setup()


def selector_mode(args):
    if args.mode == "inject":
        injectionmode()
    elif args.mode == "air":
        airmode()
    elif args.mode == "solvent":
        solventmode()


###########################################################################
# Sample Valves
###########################################################################

def sample_valve_initialize(args):

    if args.valve == 1:
        Valve1_Setup()
    elif args.valve == 2:
        Valve2_Setup()
    else:
        Valve3_Setup()


def sample_valve_chemical(args):

    v1_map, v2_map, v3_map = get_maps(args.num_chemicals)

    if args.valve == 1:
        open_valve1(args.chemical, v1_map)

    elif args.valve == 2:
        open_valve2(args.chemical, v2_map)

    else:
        open_valve3(args.chemical, v3_map)


def sample_valve_solvent(args):

    if args.valve == 1:
        Solvent_Valve1()
    elif args.valve == 2:
        Solvent_Valve2()
    else:
        Solvent_Valve3()


def sample_valve_air(args):

    if args.valve == 1:
        Air_Valve1()
    elif args.valve == 2:
        Air_Valve2()
    else:
        Air_Valve3()


###########################################################################
# Pumps
###########################################################################

PUMPS = {
    "sample1": {
        "initialize": PumpInitialize_pumpSample1,
        "withdraw": PumpWithdrawSample1,
        "withdraw_volume": PumpWithdrawSample1_Volume1,
        "inject": PumpInjection_pumpSample1,
        "full_inject": PumpFullInjection_pumpSample1,
        "empty": PumpEmpty_PumpSample1,
        "debubble": Debubble_pumpSample1,
    },
    "sample2": {
        "initialize": PumpInitialize_pumpSample2,
        "withdraw": PumpWithdrawSample2,
        "withdraw_volume": PumpWithdrawSample2_Volume2,
        "inject": PumpInjection_pumpSample2,
        "full_inject": PumpFullInjection_pumpSample2,
        "empty": PumpEmpty_PumpSample2,
        "debubble": Debubble_pumpSample2,
    },
    "sample3": {
        "initialize": PumpInitialize_pumpSample3,
        "withdraw": PumpWithdrawSample3,
        "withdraw_volume": PumpWithdrawSample3_Volume3,
        "inject": PumpInjection_pumpSample3,
        "full_inject": PumpFullInjection_pumpSample3,
        "empty": PumpEmpty_PumpSample3,
        "debubble": Debubble_pumpSample3,
    },
}


def pump_initialize(args):
    PUMPS[args.pump]["initialize"]()


def pump_withdraw(args):
    PUMPS[args.pump]["withdraw"](args.rate)


def pump_withdraw_volume(args):
    PUMPS[args.pump]["withdraw_volume"](args.rate, args.volume)


def pump_inject(args):
    PUMPS[args.pump]["inject"](args.rate, args.volume)


def pump_full_inject(args):
    PUMPS[args.pump]["full_inject"](args.rate, args.destination)


def pump_empty(args):
    PUMPS[args.pump]["empty"](args.rate)


def pump_debubble(args):
    PUMPS[args.pump]["debubble"](args.rate, args.volume)


###########################################################################
# Cleaning
###########################################################################

def cleaning(args):

    if args.routine == "solvent":
        cleaning_part1()

    elif args.routine == "hc":
        Cleaning_part2()

    elif args.routine == "hc-switch":
        Cleaning_part2_switch()

    elif args.routine == "cp":
        cleanCp()

    elif args.routine == "air-purge":
        airpurge()


###########################################################################
# Assignment
###########################################################################

def assign_all(args):

    v1, v2, v3 = generate_valve_maps(args.num_chemicals)

    assign_chemicals(
        [args.pump1, args.pump2, args.pump3],
        v1,
        v2,
        v3,
        None,
        None,
        None,
    )


###########################################################################
# Main
###########################################################################

def build_parser():

    parser = argparse.ArgumentParser(
        description="SDL Hardware Control CLI"
    )

    sub = parser.add_subparsers(dest="device", required=True)

    #######################################################################
    # selector
    #######################################################################

    selector = sub.add_parser("selector")

    selector_sub = selector.add_subparsers(dest="command", required=True)

    p = selector_sub.add_parser("initialize")
    p.set_defaults(func=selector_initialize)

    p = selector_sub.add_parser("mode")
    p.add_argument(
        "mode",
        choices=["inject", "air", "solvent"],
    )
    p.set_defaults(func=selector_mode)

    #######################################################################
    # sample valve
    #######################################################################

    valve = sub.add_parser("sample-valve")

    valve_sub = valve.add_subparsers(dest="command", required=True)

    p = valve_sub.add_parser("initialize")
    p.add_argument("--valve", type=int, choices=[1,2,3], required=True)
    p.set_defaults(func=sample_valve_initialize)

    p = valve_sub.add_parser("chemical")
    p.add_argument("--valve", type=int, choices=[1,2,3], required=True)
    p.add_argument("--chemical", required=True)
    p.add_argument("--num-chemicals", type=int, required=True)
    p.set_defaults(func=sample_valve_chemical)

    p = valve_sub.add_parser("solvent")
    p.add_argument("--valve", type=int, choices=[1,2,3], required=True)
    p.set_defaults(func=sample_valve_solvent)

    p = valve_sub.add_parser("air")
    p.add_argument("--valve", type=int, choices=[1,2,3], required=True)
    p.set_defaults(func=sample_valve_air)

    #######################################################################
    # pump
    #######################################################################

    pump = sub.add_parser("pump")
    pump_sub = pump.add_subparsers(dest="command", required=True)

    def add_pump_argument(p):
        p.add_argument(
            "--pump",
            choices=["sample1","sample2","sample3"],
            required=True,
        )

    p = pump_sub.add_parser("initialize")
    add_pump_argument(p)
    p.set_defaults(func=pump_initialize)

    p = pump_sub.add_parser("withdraw")
    add_pump_argument(p)
    p.add_argument("--rate", type=float, required=True)
    p.set_defaults(func=pump_withdraw)

    p = pump_sub.add_parser("withdraw-volume")
    add_pump_argument(p)
    p.add_argument("--rate", type=float, required=True)
    p.add_argument("--volume", type=float, required=True)
    p.set_defaults(func=pump_withdraw_volume)

    p = pump_sub.add_parser("inject")
    add_pump_argument(p)
    p.add_argument("--rate", type=float, required=True)
    p.add_argument("--volume", type=float, required=True)
    p.set_defaults(func=pump_inject)

    p = pump_sub.add_parser("full-inject")
    add_pump_argument(p)
    p.add_argument("--rate", type=float, required=True)
    p.add_argument("--destination", type=float, required=True)
    p.set_defaults(func=pump_full_inject)

    p = pump_sub.add_parser("empty")
    add_pump_argument(p)
    p.add_argument("--rate", type=float, required=True)
    p.set_defaults(func=pump_empty)

    p = pump_sub.add_parser("debubble")
    add_pump_argument(p)
    p.add_argument("--rate", type=float, required=True)
    p.add_argument("--volume", type=float, required=True)
    p.set_defaults(func=pump_debubble)

    #######################################################################
    # cleaning
    #######################################################################

    clean = sub.add_parser("cleaning")

    clean.add_argument(
        "routine",
        choices=[
            "solvent",
            "hc",
            "hc-switch",
            "cp",
            "air-purge",
        ],
    )

    clean.set_defaults(func=cleaning)

    #######################################################################
    # assign
    #######################################################################

    assign = sub.add_parser("assign")

    assign.add_argument("--pump1")
    assign.add_argument("--pump2")
    assign.add_argument("--pump3")
    assign.add_argument("--num-chemicals", type=int, required=True)

    assign.set_defaults(func=assign_all)

    return parser


def main():

    parser = build_parser()

    args = parser.parse_args()

    args.func(args)


if __name__ == "__main__":
    main()