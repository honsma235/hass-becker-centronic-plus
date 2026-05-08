# Becker Centronic Plus for Home Assistant

> [!WARNING]
> **Work in Progress:** This integration is currently in early development and is not considered production-ready. Use it with caution and expect potential breaking changes.

This custom integration allows you to control Becker Centronic Plus shutter motors and devices using the official Becker Centronic Plus USB Stick, bypassing the need for a CentralControl CC41 unit.

## Features

- **Cover Support**: Full control of shutters including open, close, stop, and absolute position (0-100%).
- **Status Feedback**: Real-time position and state updates via intelligent backoff polling.
- **Advanced Controls**:
  - **Fly Screen Protection**: Toggle via a switch entity.
  - **Presets**: Buttons to trigger "Preset 1" and "Preset 2".
  - **Identify**: Button to make the motor "jog" for identification.
- **Diagnostics**: Sensors for "Blocked" and "Overheated" states.
- **Name Sync**: Changing a device name in Home Assistant automatically syncs the name to the Becker hardware.
- **USB Discovery**: Automatically detects the Becker USB stick when plugged into the host.

## Requirements

- **Hardware**: Becker Centronic Plus USB stick (ordering code `4036 200 001 0` or `4036 000 009 0`).
   > [!IMPORTANT]
   > This integration does **not** work with the older **non-Plus** Centronic USB sticks (`4035 200 041 0` or `4035 000 041 0`)!

## Known Limitations

- Currently only tested with roller shutter drives of the **C01 PLUS** series.
- It likely does not yet support the **EVO 20 R PLUS** series or sun protection drives of the **Cxx PLUS** series.   
   > Support for additional Centronic Plus drive series could be added if their request/response protocol is analyzed.
- Does not support pairing the Becker USB stick with covers or performing initial commissioning. This functionality is not yet implemented to ensure setup reliability.
   > [!TIP]
   > Pairing and initial commissioning (e.g., setting end-stop positions) can be performed using a computer or mobile device with the [Becker Tool](https://l.ead.me/beypHO) app, available on the Microsoft Store, Google Play Store, and Apple App Store.

   > [!CAUTION]
   > Configuring end-stops is a critical task. Incorrect settings can lead to hardware damage. It is your responsibility to ensure you follow the manufacturer's instructions or consider hiring a professional installer.

## Installation

### Option 1: HACS (Recommended)
1. Open HACS in Home Assistant.
2. Click the three dots in the top right and select **Custom repositories**.
3. Add this repository URL and select **Integration** as the category.
4. Click **Install**.
5. Restart Home Assistant.

### Option 2: Manual
1. Copy the `custom_components/becker_centronic_plus` folder to your Home Assistant `config/custom_components` directory.
2. Restart Home Assistant.

## Configuration

1. **USB Discovery**: Plug in your Becker USB stick. Home Assistant should automatically notify you that a new device has been discovered. Follow the prompts to configure it.
   > If your USB stick is not auto-discovered, please open an issue or PR with the hardware attributes found in **Settings** -> **System** -> **Hardware** -> **All hardware**.
2. **Manual Setup**:
   - Go to **Settings** -> **Devices & Services**.
   - Click **Add Integration**.
   - Search for **Becker Centronic Plus** and configure it.
   - Select the correct serial port (e.g., `/dev/serial/by-id/usb-Becker-Antriebe_GmbH_CentronicPlus_Stick-if00`).


## Troubleshooting

If the integration fails to connect, ensure the Home Assistant user has permissions to access the serial port (usually the `dialout` group in Linux environments).
