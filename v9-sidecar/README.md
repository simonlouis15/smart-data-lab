# V9 Sidecar CLI

A side-effect-free, class-based command-line wrapper around the V9 pump and
selector-valve hardware. It reimplements the serial protocols from the
`V9-TC-EC` scripts (`SelectorValvesV9.py`, `SyringePumpsHTPumpTCV9.py`) in the
same style as the original `backend/` CLI so it can be bundled into a single
`.exe` and used as a Tauri sidecar.

## Why not import the V9 scripts directly?

The `V9-TC-EC` modules are not safe to import into a sidecar as-is:

- They open every serial port at **import time** with **hardcoded COM ports**.
- Some modules **move hardware at import** (e.g. the bottom of
  `SyringePumpsHTPumpTCV9.py` initializes and injects pump 1).
- There is no CLI entry point; only `Campaign_26Jars-V9.py` has a `main()`, and
  it runs a whole campaign.

This package keeps the exact command strings and scaling (`GO`, `NP`, `AK`,
`AM3`, `CP`; `/<num>...R`, `EV`/`IV`/`OV`, `x * 20` units) but makes ports and
parameters explicit and defers all I/O until a command runs.

## Files

- `devices.py` — `SerialDevice`, `SelectorValve`, `Pump` drivers + helpers.
- `cli.py` — `argparse` entry point with `valve` and `pump` subcommands.

## Install & run (dev)

This project uses [uv](https://docs.astral.sh/uv/). Dependencies are declared in
`pyproject.toml` and locked in `uv.lock`; `uv run` auto-creates/updates `.venv`.

```bash
uv sync                                                   # create .venv + install deps
uv run cli.py valve --port COM9 --positions 10 --mode solvent
```

`[tool.uv] system-certs = true` is set in `pyproject.toml` so uv uses the OS
certificate store (the default bundle fails PyPI TLS in this environment).

A plain `pip install -r requirements.txt` still works if you prefer a manually
managed environment.

## Valve commands

The same driver handles the 10-port main valve and the 28-port per-pump valves;
`--positions` selects which (`NP10` vs `NP28`).

```bash
# 10-port main flow valve: sample (GO03) / air (GO09) / solvent (GO01)
python cli.py valve --port COM9  --positions 10 --mode solvent

# 28-port valve: route chemical "C" given 26 chemicals in the campaign
python cli.py valve --port COM3  --positions 28 --chemical C --num-chemicals 26

# 28-port valve reserved ports: solvent=27, air=28
python cli.py valve --port COM3  --positions 28 --preset air

# Any valve: move to a raw position number
python cli.py valve --port COM11 --positions 28 --position 5
```

## Pump commands

```bash
python cli.py pump --port COM10 --pump-num 1 --option initialize
python cli.py pump --port COM10 --option withdraw       --speed 300 --position 6000
python cli.py pump --port COM10 --option inject         --rate 0.3  # mL/min; converts like pump_flow_rate
python cli.py pump --port COM10 --option full-injection --rate 10   --position 4500
python cli.py pump --port COM10 --option empty          --rate 10
python cli.py pump --port COM10 --option debubble       --rate 5    --duration 6000
python cli.py pump --port COM10 --option clean          --rate 10   --speed 300
python cli.py pump --port COM10 --option query-position
python cli.py pump --port COM10 --option stop
```

Reference COM ports observed in the V9 scripts (verify against your rig):

| Device | Port | Notes |
|---|---|---|
| Main selector valve | COM9 | 10-port |
| Pump-1 chemical valve | COM3 | 28-port |
| Pump-2 chemical valve | COM4 | 28-port |
| Pump-3 chemical valve | COM11 | 28-port |
| Sample pump 1 / 2 / 3 | COM10 / COM17 / COM16 | |
| Solvent pump | COM6 | |
| HC sample / reference pump | COM14 / COM5 | |
| TC reference pump | COM13 | |

## Bundling as a Tauri sidecar

Build a one-file executable with PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --name v9-sidecar cli.py
```

Then place/rename the binary using Tauri's target-triple convention (e.g.
`v9-sidecar-x86_64-pc-windows-msvc.exe`), register it under
`tauri.conf.json > bundle > externalBin`, and invoke it from Rust with the same
subcommand/argument strings shown above — exactly how the original backend CLI
was used.
