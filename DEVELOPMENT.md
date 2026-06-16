# USB Serial Passthrough via usbipd (WSL2 & Devcontainer)

## 1. Windows Host Setup (One-time)
Open **PowerShell (Admin)** to install and list devices:
```powershell
# Install usbipd-win
winget install --interactive --exact dorssel.usbipd-win

# List USB devices to find the BUSID (e.g., 1-4)
usbipd list

# Bind the device to allow sharing
usbipd bind --force --busid <BUSID>
```

Don't forget to unbind, once you are done:
```powershell
usbipd unbind --busid <BUSID>
```

## 2. Attach Device to WSL
Run this in a **normal PowerShell** (keep it open or automate it):
```powershell
# Auto-attach whenever the device is plugged in
usbipd attach --wsl --busid <BUSID> --auto-attach
```
