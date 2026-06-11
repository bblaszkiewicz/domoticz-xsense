# Domoticz-xsense

Development
-----------

This library is in an early development stage.


### Setup

1. Copy the repository contents into a Domoticz Python plugin folder. Domoticz
   needs the top-level `plugin.py` file together with the `xsense` package and
   the `xsense_helper.py` runner.
2. Configure the plugin in Domoticz with:
   - `Mode1` - XSense username
   - `Mode2` - XSense password
   - `Mode3` - polling interval in seconds, default `60`
3. Restart the plugin.

For every detected `XS01-WX` sensor, the plugin creates three Domoticz devices
named `<deviceSN>_alarmStatus`, `<deviceSN>_muteStatus` and
`<deviceSN>_ledLight`.
