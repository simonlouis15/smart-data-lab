# Stop the script immediately if any command fails
$ErrorActionPreference = "Stop"

# Navigate into the backend directory
Set-Location backend

# Run PyInstaller to package the application
pyinstaller __main__.spec --noconfirm

# Copy and rename the executable for the Tauri sidecar configuration
Copy-Item dist\__main__.exe ..\src-tauri\__main__-x86_64-pc-windows-msvc.exe -Force

# Return safely to the root directory
Set-Location ..

# How to Use: PowerShell -ExecutionPolicy Bypass -File .\build-sidecar.ps1
