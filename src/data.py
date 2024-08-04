from dataclasses import dataclass, field
from json import loads, dumps
from datetime import datetime
from typing import Dict, Any, Union
from enum import Enum

@dataclass
class SensorData:
    temperature: float
    temperature_unit: str
    humidity: float
    pressure: float
    heat_index: float
    pressure_delta: float = field(repr=False, init=False)
    time: float = field(repr=False, init=False)

    def __post_init__(self):
        self.time = datetime.now().timestamp()

    def to_dict(self, isIso: bool = False):
        ret = {"temperature": self.temperature, "temperature_unit": self.temperature_unit, "humidity": self.humidity, "pressure": self.pressure, "heatindex": self.heat_index, "pressure_delta": self.pressure_delta}
        if isIso: ret["time"] = datetime.fromtimestamp(self.time, tz=datetime.now().astimezone().tzinfo).replace(microsecond=0).isoformat()
        else: ret["time"] = datetime.fromtimestamp(self.time).strftime(r"%Y.%B.%d. %H:%M:%S")
        ret["temperature_color"] = temperature_to_hue(self.temperature)
        ret["heatindex_color"] = temperature_to_hue(self.heat_index)
        return ret
    
    def __repr__(self) -> dict:
        ret = {"temperature": self.temperature, "temperature_unit": self.temperature_unit, "humidity": self.humidity, "pressure": self.pressure, "heatindex": self.heat_index, "pressure_delta": self.pressure_delta}
        ret["time"] = datetime.fromtimestamp(self.time).strftime(r"%Y.%B.%d. %H:%M:%S")
        return ret

    def to_json(self):
        ret = {"temperature": self.temperature, "temperature_unit": self.temperature_unit, "humidity": self.humidity, "pressure": self.pressure, "heatindex": self.heat_index, "pressure_delta": self.pressure_delta}
        ret["time"] = datetime.fromtimestamp(self.time).strftime(r"%Y.%B.%d. %H:%M:%S")
        return dumps(ret)
    
    def __lt__(self, other: Any) -> bool:
        if (isinstance(other, SensorData)):
            return self.time < other.time
        raise TypeError(f"'<' operator not supported between 'SensorData' and '{type(other)}'")

    def set_delta_compared_to(self, other: Union["SensorData", None]) -> None:
        if (other is None): self.pressure_delta = 0
        else: self.pressure_delta = self.pressure - other.pressure

    @staticmethod
    def from_json(data: str) -> "SensorData":
        tmp = loads(data)
        return SensorData(float(tmp["temperature"]), tmp["temperature_unit"], float(tmp["humidity"]), float(tmp["pressure"]), float(tmp["heat_index"]))
    
@dataclass
class Recepient:
    id: int
    interface: int
    alert_on_falling: bool
    alert_on_rising: bool
    alert_on_bell: bool

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "interface": self.interface, "alert_on_falling": self.alert_on_falling, "alert_on_rising": self.alert_on_rising, "alert_on_bell": self.alert_on_bell}

    @staticmethod
    def from_json(data: Dict[str, Any]) -> "Recepient":
        return Recepient(data["id"], data["interface"], data["alert_on_falling"], data["alert_on_rising"], data["alert_on_bell"])

class Thresholds(Enum):
    PRESSURE_POSITIVE = 200
    PRESSURE_NEGATIVE = -200
    HUMIDITY_POSITIVE = 0.2
    HUMIDITY_NEGATIVE = -0.2
    TEMPERATURE_POSITIVE = 0.5
    TEMPERATURE_NEGATIVE = -0.5

def temperature_to_hue(temp: float) -> float:
    if temp < 0:
        return translate(temp, 0, -20, 170, 200)
    elif temp < 23:
        return translate(temp, 23, 0, 150, 170)
    elif temp < 26:
        return translate(temp, 26, 23, 100, 150)
    else:
        return translate(temp, 35, 26, 0, 50)

def translate(value, inmin, inmax, outmin, outmax):
        inspan = inmax - inmin
        outspan = outmax - outmin
        scaled = float(value - inmin) / float(inspan)
        return round(outmin + (scaled * outspan), 2)
