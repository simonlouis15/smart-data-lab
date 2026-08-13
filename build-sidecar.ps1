# Stop the script immediately if any command fails
$ErrorActionPreference = "Stop"

# Navigate into the v9-sidecar directory
Set-Location v9-sidecar

# Ensure the virtual environment is in sync with the locked dependencies
uv sync

# Run PyInstaller (via uv) to package the CLI into a single executable
uv run pyinstaller v9-sidecar.spec --noconfirm

# Copy and rename the executable using Tauri's target-triple convention so it
# is picked up as the `v9-sidecar` external binary (see tauri.conf.json).
Copy-Item dist\v9-sidecar.exe ..\src-tauri\v9-sidecar-x86_64-pc-windows-msvc.exe -Force

# Return safely to the root directory
Set-Location ..

# How to Use: PowerShell -ExecutionPolicy Bypass -File .\build-sidecar.ps1
