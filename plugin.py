from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import Domoticz  # type: ignore
except ImportError:  # pragma: no cover - local development fallback
    class _StubDevice:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.Name = kwargs.get("Name")
            self.Unit = kwargs.get("Unit")
            self.TypeName = kwargs.get("TypeName")
            self.nValue = 0
            self.sValue = ""
            self.LastLevel = 0

        def Create(self):
            Devices[self.Unit] = self
            return True

        def Update(self, nValue=0, sValue="", **kwargs):
            self.nValue = nValue
            self.sValue = sValue
            for key, value in kwargs.items():
                setattr(self, key, value)
            return True

    class _StubDomoticz:
        def Log(self, message):
            print(message)

        def Debug(self, message):
            print(message)

        def Error(self, message):
            print(message)

        def Status(self, message):
            print(message)

        def Heartbeat(self, seconds):
            self._heartbeat = seconds

        def Device(self, **kwargs):
            return _StubDevice(**kwargs)

    Domoticz = _StubDomoticz()  # type: ignore
    Devices = {}
    Parameters = {}
else:
    Devices = globals().get("Devices", {})
    Parameters = globals().get("Parameters", {})

from xsense import XSense
from xsense.exceptions import APIFailure, AuthFailed, NotFoundError, SessionExpired


FIELD_SPECS = {
    "alarmStatus": {
        "type_name": "Switch",
        "formatter": lambda value: "On" if _to_bool(value) else "Off",
        "nvalue": lambda value: 1 if _to_bool(value) else 0,
    },
    "muteStatus": {
        "type_name": "Switch",
        "formatter": lambda value: "On" if _to_bool(value) else "Off",
        "nvalue": lambda value: 1 if _to_bool(value) else 0,
    },
    "batInfo": {
        "type_name": "Percentage",
        "formatter": lambda value: str(_to_int(value)),
        "nvalue": lambda value: 0,
    },
    "ledLight": {
        "type_name": "Switch",
        "formatter": lambda value: "On" if _to_bool(value) else "Off",
        "nvalue": lambda value: 1 if _to_bool(value) else 0,
    },
}

TRACKED_TYPES = {"XS01-WX"}


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class XSenseDomoticzPlugin:
    def __init__(self):
        self.api: Optional[XSense] = None
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.poll_seconds = 60
        self.ready = False
        self._known_units: Dict[str, int] = {}

    def log(self, message: str):
        Domoticz.Log(f"XSense: {message}")

    def error(self, message: str):
        Domoticz.Error(f"XSense: {message}")

    def start(self):
        self.poll_seconds = max(10, self._read_int_parameter("Mode3", default=60))
        Domoticz.Heartbeat(self.poll_seconds)

        self.username, self.password = self._read_credentials()
        if not self.username or not self.password:
            self.error("Brak loginu lub hasla. Ustaw Mode1/Mode2 albo .env.")
            self.ready = False
            return

        self.log(f"Start, odswiezanie co {self.poll_seconds}s")
        self.ready = self._connect()
        if self.ready:
            self.sync()

    def stop(self):
        if self.api:
            self.api.close()
        self.ready = False

    def heartbeat(self):
        if not self.ready:
            self.ready = self._connect()
            if not self.ready:
                return

        self.sync()

    def _connect(self) -> bool:
        try:
            api = XSense()
            api.init()
            api.login(self.username, self.password)
            api.load_all()
            self.api = api
            self.log("Zalogowano do XSense")
            return True
        except (AuthFailed, APIFailure, SessionExpired, OSError, ValueError) as exc:
            self.error(f"Logowanie nie powiodlo sie: {exc}")
            self.api = None
            return False

    def sync(self):
        if not self.api:
            return

        try:
            for house in self.api.houses.values():
                try:
                    self.api.get_house_state(house)
                except NotFoundError:
                    self.log(f"Pominieto stan domu {house.name}: brak danych")

                for station in house.stations.values():
                    self._sync_station(station)
        except SessionExpired:
            self.log("Sesja wygasla, probuje zalogowac sie ponownie")
            self.ready = self._connect()
        except APIFailure as exc:
            self.error(f"Blad XSense: {exc}")

    def _sync_station(self, station):
        self._ensure_station_devices(station)

        try:
            self.api.get_station_state(station)
        except NotFoundError:
            self.log(f"Pominieto stan {station.sn}: brak danych info")
        except APIFailure as exc:
            self.error(f"Nie moge pobrac stanu {station.sn}: {exc}")
            return

        if station.devices:
            try:
                self.api.get_state(station)
            except APIFailure as exc:
                self.error(f"Nie moge pobrac stanu urzadzen {station.sn}: {exc}")

        self._update_station_devices(station)

    def _should_track_station(self, station) -> bool:
        if station.type in TRACKED_TYPES:
            return True
        return any(field in station.data for field in FIELD_SPECS)

    def _device_name(self, station, field: str) -> str:
        return f"{station.sn}_{field}"

    def _find_device(self, name: str):
        for unit, device in Devices.items():
            if getattr(device, "Name", None) == name:
                try:
                    self._known_units[name] = int(unit)
                except (TypeError, ValueError):
                    pass
                return device
        return None

    def _next_unit(self) -> int:
        used = set()
        for unit in Devices.keys():
            try:
                used.add(int(unit))
            except (TypeError, ValueError):
                continue

        unit = 1
        while unit in used:
            unit += 1
        return unit

    def _ensure_device(self, name: str, type_name: str):
        if device := self._find_device(name):
            return device

        unit = self._known_units.get(name) or self._next_unit()
        device = Domoticz.Device(
            Name=name,
            Unit=unit,
            TypeName=type_name,
            Used=1,
        )
        device.Create()
        self._known_units[name] = unit
        self.log(f"Utworzono urzadzenie: {name} (Unit {unit}, {type_name})")
        return device

    def _ensure_station_devices(self, station):
        if not self._should_track_station(station):
            return

        for field, spec in FIELD_SPECS.items():
            self._ensure_device(self._device_name(station, field), spec["type_name"])

    def _update_station_devices(self, station):
        for field, spec in FIELD_SPECS.items():
            if field not in station.data and field != "batInfo":
                continue

            value = station.data.get(field)
            if field == "batInfo" and value is None:
                value = station.data.get("batLevel")
            if value is None:
                continue

            name = self._device_name(station, field)
            device = self._find_device(name)
            if not device:
                continue

            try:
                n_value = spec["nvalue"](value)
                s_value = spec["formatter"](value)
                device.Update(nValue=n_value, sValue=s_value)
            except Exception as exc:
                self.error(f"Nie moge zaktualizowac {name}: {exc}")

    def _read_int_parameter(self, key: str, default: int) -> int:
        raw = Parameters.get(key)
        if raw is None or raw == "":
            return default
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    def _read_credentials(self):
        username = Parameters.get("Mode1") or os.getenv("XSENSE_USERNAME")
        password = Parameters.get("Mode2") or os.getenv("XSENSE_PASSWORD")

        if username and password:
            return username, password

        env_path = Path(".env")
        if env_path.exists():
            loaded = {}
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                loaded[key.strip().lower()] = value.strip()

            username = username or loaded.get("username")
            password = password or loaded.get("password")

        return username, password


_plugin = XSenseDomoticzPlugin()


def onStart():
    _plugin.start()


def onStop():
    _plugin.stop()


def onHeartbeat():
    _plugin.heartbeat()
