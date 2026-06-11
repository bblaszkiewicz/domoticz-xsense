# Domoticz-xsense

This repository is a fork of [theosnel/python-xsense](https://github.com/theosnel/python-xsense).

## Overview

Domoticz-xsense is a Domoticz Python plugin for XSense Home Security devices.
It currently targets `XS01-WX` Wi-Fi smoke alarms and exposes their status as
individual Domoticz devices.

The plugin authenticates with XSense using a username and password, polls the
cloud API, and creates Domoticz devices with names based on the XSense
`deviceSN`.

## Features

- Reads XSense account data with username and password
- Polls alarm state from XSense on a fixed interval
- Creates Domoticz devices automatically for each detected sensor
- Uses device names based on `deviceSN`
- Tracks:
  - `alarmStatus`
  - `muteStatus`
  - `ledLight`

## Installation

1. Copy the repository contents into your Domoticz Python plugins folder.
2. Make sure these files are present in the plugin directory:
   - `plugin.py`
   - `xsense_helper.py`
   - `xsense/`
3. Restart or reload the plugin in Domoticz.
4. Configure the plugin parameters:
   - `Mode1` - XSense username
   - `Mode2` - XSense password
   - `Mode3` - polling interval in seconds, default `60`

## Domoticz Device Mapping

| XSense field | Domoticz device name | Type |
| --- | --- | --- |
| `alarmStatus` | `<deviceSN>_alarmStatus` | `Switch` |
| `muteStatus` | `<deviceSN>_muteStatus` | `Switch` |
| `ledLight` | `<deviceSN>_ledLight` | `Switch` |

Example for sensor `002C1F75`:

- `002C1F75_alarmStatus`
- `002C1F75_muteStatus`
- `002C1F75_ledLight`

## Configuration

The plugin uses the following Domoticz parameters:

- `Mode1` - XSense username
- `Mode2` - XSense password
- `Mode3` - polling interval in seconds

If `Mode1` and `Mode2` are not filled in Domoticz, the plugin also checks the
environment variables `XSENSE_USERNAME` and `XSENSE_PASSWORD`.

## Supported Devices

Currently supported:

- `XS01-WX`

Additional XSense device types can be added later if needed.

## Development

This project is still in active development and is primarily intended as a
Domoticz integration layer for the upstream XSense client library.

## Credits

Original upstream project:

- [theosnel/python-xsense](https://github.com/theosnel/python-xsense)
