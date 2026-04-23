from datetime import datetime

from smdb_api import API, Message, Interface, Privilege
from smdb_logger import Logger, LEVEL
from typing import Dict, List, Any, Union, cast
from smdb_web_server import HTMLServer, UrlData
from threading import Thread, Event
from time import sleep
from os import path, mkdir
from data import SensorData, Recipient, Thresholds, temperature_to_hue, translate, TemperatureUnit
from connector import Client
from slope_detector import Direction, detect_slope
from json import load, dumps, dump, JSONDecodeError

ROOT = path.dirname(path.dirname(__file__))
TEMPLATES = {"index": "PATH|data/template/index.html", "chart": "PATH|data/template/chart.html"}
STATIC = {"styles": "PATH|data/static/styles.css", "scripts": "PATH|data/static/scripts.js", "colorschema": "PATH|data/static/colorschema.css", "favicon":"PATH|data/static/favicon.svg", "charts": "PATH|data/static/charts.js"}

up_arrow = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
    <!--!Font Awesome Free 6.5.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.-->
    <path d="M233.4 105.4c12.5-12.5 32.8-12.5 45.3 0l192 192c12.5 12.5 12.5 32.8 0 45.3s-32.8 12.5-45.3 0L256 173.3 86.6 342.6c-12.5 12.5-32.8 12.5-45.3 0s-12.5-32.8 0-45.3l192-192z"/>
    <title>{TITLE}</title>
</svg>
"""
high_arrow = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
    <!--!Font Awesome Free 6.5.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.-->
    <path d="M246.6 41.4c-12.5-12.5-32.8-12.5-45.3 0l-160 160c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L224 109.3 361.4 246.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3l-160-160zm160 352l-160-160c-12.5-12.5-32.8-12.5-45.3 0l-160 160c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L224 301.3 361.4 438.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3z"/>
    <title>{TITLE}</title>
</svg>
"""
down_arrow = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
    <!--!Font Awesome Free 6.5.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.-->
    <path d="M233.4 406.6c12.5 12.5 32.8 12.5 45.3 0l192-192c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L256 338.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l192 192z"/>
    <title>{TITLE}</title>
</svg>
"""
low_arrow = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
    <!--!Font Awesome Free 6.5.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.-->
    <path d="M246.6 470.6c-12.5 12.5-32.8 12.5-45.3 0l-160-160c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0L224 402.7 361.4 265.4c12.5-12.5 32.8-12.5 45.3 0s12.5 32.8 0 45.3l-160 160zm160-352l-160 160c-12.5 12.5-32.8 12.5-45.3 0l-160-160c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0L224 210.7 361.4 73.4c12.5-12.5 32.8-12.5 45.3 0s12.5 32.8 0 45.3z"/>
    <title>{TITLE}</title>
</svg>
"""
stagnating = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
    <!--!Font Awesome Free 6.5.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.-->
    <path d="M432 256c0 17.7-14.3 32-32 32L48 288c-17.7 0-32-14.3-32-32s14.3-32 32-32l352 0c17.7 0 32 14.3 32 32z"/>
    <title>{TITLE}</title>
</svg>
"""

class Bell:
    def __init__(self, config_path: str):
        self.config_path = config_path
        config = self.read_config()
        self.logger = Logger("Bell.log", log_folder=path.join(ROOT, "data"), level=LEVEL.DEBUG, use_caller_name=True)
        self.api = API.from_config(path.join(ROOT, "data", "api.cfg"))
        self.web_server = HTMLServer(config["SERVER"]["host"], config["SERVER"]["port"], ROOT, logger=self.logger)
        self.sensor_history: List[SensorData] = []
        self.request_time: int = cast(int, cast(object, config["request_time"]))
        self.recipients: List[Recipient] = [Recipient.from_json(x) for x in config["recipients"]]
        self.bell_connector = Client(config["BELL"]["host"], config["BELL"]["port"], self.logger)
        self.bell_connector.add_handler(self.bell_callback, "Bell")
        self.bell_connector.add_handler(self.bell_timeout_callback, "timeout")
        self.stop_event = Event()
        self.main_thread: Thread | None = None
        self.last_save = datetime.now()

    def prepare_webpage(self):
        self.web_server.add_url_rule("/", self.__index)
        self.web_server.add_url_rule("/get", self.__get_weather)
        self.web_server.add_url_rule("/save", self.__save)
        self.web_server.add_url_rule("/chart", self.__chart)
    
    def prepare_api(self):
        self.api.create_function("AddRecepient", "Adds recepient to the bell and weather alerts. At least one argument is required, if multiple is present separate them by ','!\nUsage: &AddRecepient [falling|rising|bell]\nCategory: NETWORK", self.add_recipient, privilege=Privilege.OnlyAdmin, needs_arguments=True)

    def save_datapoints(self) -> None:
        if not path.exists(path.join(ROOT, "data", "powerbi")):
            mkdir(path.join(ROOT, "data", "powerbi"))
        with open(path.join(ROOT, "data", "powerbi", f"data_history{datetime.now().strftime(r'%Y.%m.%d')}.json"), "w") as fp:
            fp.writelines(dumps([item.to_dict() for item in self.sensor_history]))

    def is_above_warning_temperature(self, sensor_data: SensorData) -> bool:
        if sensor_data.temperature_unit == TemperatureUnit.C:
            return sensor_data.temperature > 50.0
        else: # TemperatureUnit.F
            return sensor_data.temperature > 122.00

    def __save(self, _) -> str:
        self.save_datapoints()
        return "Done"

    def __get_weather(self, data: UrlData) -> str | None:
        if "current" in data.query:
            self.fetch_data()
            self.sensor_history.sort(reverse=True)
            return self.sensor_history[0].to_json()
        elif "history" in data.query:
            if len(self.sensor_history) >= 5:
                self.sensor_history.sort(reverse=True)
                data = {"items": [item.to_dict() for item in self.sensor_history[1:5]], "refference": self.sensor_history[5].to_dict()}
            else:
                data = {}
            return dumps(data)
        elif "chart" in data.query:
            self.sensor_history.sort(reverse=True)
            return dumps({"items": [it.to_dict(is_iso=True, convert_pressure=True) for it in self.sensor_history]})
        return None

    def __chart(self, _) -> str:
        return self.web_server.render_template_file("chart", page_title="Charts")

    def __index(self, _) -> str:
        self.sensor_history.sort(reverse=True)
        current_data = self.sensor_history[0]
        previous = self.sensor_history[1] if len(self.sensor_history) > 1 else None
        temperature_dif = previous.temperature - current_data.temperature if previous is not None else 0
        humidity_dif = previous.humidity - current_data.humidity if previous is not None else 0
        heat_index_dif = previous.heat_index - current_data.heat_index if previous is not None else 0
        pressure_dif = previous.pressure - current_data.pressure if previous is not None else 0
        temperature_hue = int(temperature_to_hue(current_data.temperature))
        heat_index_hue = int(temperature_to_hue(current_data.heat_index))
        pressure_p = int(translate(current_data.pressure / 100, 960, 1040, 0, 100))
        return self.web_server.render_template_file(
            "index",
            time=current_data.time_to_string(False),
            page_title="Weather",
            temperature=str(round(current_data.temperature, 1)),
            temperaturep=str(temperature_hue),
            temperature_unit=current_data.temperature_unit,
            temperaturechc = "blue" if temperature_dif < 0 else "red" if temperature_dif > 0 else "white",
            temperaturechd = (high_arrow if temperature_dif < -0.5 else up_arrow if temperature_dif < 0 else low_arrow if temperature_dif > 0.5 else down_arrow if temperature_dif > 0 else stagnating).replace("{TITLE}", "Temperature"),
            humidity=str(round(current_data.humidity, 1)),
            humidityp=str(int(current_data.humidity)),
            humidityless="" if current_data.humidity > 50 else " less",
            humiditychc = "blue" if humidity_dif < 0 else "red" if humidity_dif > 0 else "white",
            humiditychd = (high_arrow if humidity_dif < -0.5 else up_arrow if humidity_dif < 0 else low_arrow if humidity_dif > 0.5 else down_arrow if humidity_dif > 0 else stagnating).replace("{TITLE}", "Humidity"),
            heatindex=str(round(current_data.heat_index, 1)),
            heatindexp=str(heat_index_hue),
            heatindexchc = "blue" if heat_index_dif < 0 else "red" if heat_index_dif > 0 else "white",
            heatindexchd = (high_arrow if heat_index_dif < -0.5 else up_arrow if heat_index_dif < 0 else low_arrow if heat_index_dif > 0.5 else down_arrow if heat_index_dif > 0 else stagnating).replace("{TITLE}", "Heat Index"),
            pressure=str(round(current_data.pressure / 100, 1)),
            pressurep=str(pressure_p),
            pressureless="" if pressure_p > 50 else " less",
            pressurechc = "blue" if pressure_dif < 0 else "red" if pressure_dif > 0 else "white",
            pressurechd = (high_arrow if pressure_dif < -0.5 else up_arrow if pressure_dif < 0 else low_arrow if pressure_dif > 0.5 else down_arrow if pressure_dif > 0 else stagnating).replace("{TITLE}", f"{pressure_dif}")
        )

    def start(self):
        self.api.validate()
        self.bell_connector.start()
        self.fetch_data()
        self.prepare_webpage()
        self.prepare_api()
        self.web_server.serve_forever_threaded(TEMPLATES, STATIC, "Home Weather Station")
        if self.main_thread is not None: return
        self.main_thread = Thread(target=self.main_loop)
        self.main_thread.name = "Bell main loop"
        self.main_thread.start()
        if self.request_time > 10:
            Thread(target=self.hearth_beat, name="Bell Hearth Beat thread").start()

    def restart(self):
        self.main_thread = Thread(target=self.main_loop)
        self.main_thread.name = "Bell main loop"
        self.main_thread.start()

    def is_alive(self) -> bool:
        return self.main_thread is not None and self.main_thread.is_alive()

    def hearth_beat(self):
        while not self.stop_event.is_set():
            if self.bell_connector.is_alive():
                self.bell_connector.send("ping")
            else:
                self.logger.error("Bell connector failed!")
                self.logger.debug("Re-creating bell connector")
                self.bell_connector.start()
            self.stop_event.wait(10)

    def stop(self):
        self.api.close("Program terminating")
        self.stop_event.set()
        self.web_server.stop()
        self.bell_connector.stop()
    
    def send_message_to_all_user(self, message: str):
        for person in self.recipients:
            if not person.alert_on_bell:
                return
            self.api.send_message(message, Interface(person.interface), person.id)

    def bell_timeout_callback(self):
        self.send_message_to_all_user("Bell is not connected!")

    def bell_callback(self):
        if self.logger is not None: self.logger.trace("Bell rang")
        for person in self.recipients:
            if not person.alert_on_bell:
                continue
            self.api.send_message("Bell", Interface(person.interface), person.id)
    
    def get_trends(self) -> List[Direction]:
        self.sensor_history.sort()
        pressure_dir = detect_slope([item.pressure for item in self.sensor_history], Thresholds.PRESSURE_POSITIVE, Thresholds.PRESSURE_NEGATIVE)
        temperature_dir = detect_slope([item.temperature for item in self.sensor_history], Thresholds.TEMPERATURE_POSITIVE, Thresholds.TEMPERATURE_NEGATIVE)
        humidity_dir = detect_slope([item.humidity for item in self.sensor_history], Thresholds.HUMIDITY_POSITIVE, Thresholds.HUMIDITY_NEGATIVE)
        return [pressure_dir, temperature_dir, humidity_dir]

    def fetch_data(self) -> None:
        response = self.bell_connector.send("getSensors")
        try:
            sensor_data = SensorData.from_json(response)
            if self.is_above_warning_temperature(sensor_data):
                response = self.bell_connector.send("getSensors")
                try:
                    sensor_data = SensorData.from_json(response)
                except JSONDecodeError:
                    if self.logger is not None: self.logger.warning(f"Response was not JSON deserializable in inner request: `{response}`")
                if self.is_above_warning_temperature(sensor_data):
                    self.send_message_to_all_user(f"To high temperature detected: {sensor_data.temperature}")
            if len(self.sensor_history) > 0:
                self.sensor_history.sort(reverse=True)
                sensor_data.set_delta_compared_to(self.sensor_history[0])
            else:
                sensor_data.set_delta_compared_to(None)
            self.sensor_history.insert(0, sensor_data)
            if (datetime.now() - self.last_save).total_seconds() > 86400:
                self.save_datapoints()
                self.sensor_history = [sensor_data]
                self.last_save = datetime.now()
        except JSONDecodeError:
            if self.logger is not None: self.logger.warning(f"Response was not JSON deserializable: `{response}`")

    def main_loop(self):
        message_sent = False
        while not self.stop_event.is_set():
            try:
                self.fetch_data()
                (pressure_dir, temperature_dir, humidity_dir) = self.get_trends()
                if pressure_dir == Direction.FALLING and not message_sent:
                    for person in self.recipients:
                        if not person.alert_on_falling: continue
                        self.api.send_message("Pressure is falling rapidly!", Interface(person.interface), person.id)
                    message_sent = True
                elif pressure_dir == Direction.RISING and not message_sent:
                    for person in self.recipients:
                        if not person.alert_on_rising: continue
                        self.api.send_message("Pressure is rising rapidly!", Interface(person.interface), person.id)
                    message_sent = True
                elif pressure_dir == Direction.STATIC:
                    message_sent = False
                if abs(self.sensor_history[-1].pressure_delta) > 25 and not message_sent:
                    for person in self.recipients:
                        self.api.send_message(f"The pressure abruptly {'fallen' if self.sensor_history[-1].pressure_delta < 0 else 'risen'} {abs(self.sensor_history[-1].pressure_delta)} mbar between two measurements.", Interface(person.interface), person.id)
                    message_sent = True
                self.stop_event.wait(self.request_time)
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt!")
                self.stop()
            except Exception as ex:
                self.logger.error(f"Exception: {ex}")

    def read_config(self) -> Dict[str, Union[List[Dict[str, Any]], Dict[str, Any]]]:
        if not path.exists(self.config_path):
            self.write_config({"request_time": 60, "SERVER": { "host": "LOCAL IP", "port": 6969 }, "BELL": { "host": "ESP IP", "port": 6900 }, "recipients": []})
            raise FileNotFoundError("Config file not found. Please fill in the newly created config file!")
        config: Dict[str, Union[List[Dict[str, Any]], Dict[str, Any]]] = {}
        with open(self.config_path, "r") as fp:
            config = load(fp)
        if "recepients" in config:
            # Fixing typo in old config
            config["recipients"] = config.pop("recepients")
            self.write_config(config)
        return config

    def write_config(self, config: Dict[str, Union[List[Dict[str, Any]], Dict[str, Any]]]) -> None:
        with open(self.config_path, "w") as fp:
            dump(config, fp)

    def add_recipient_to_config(self, new: Recipient) -> None:
        config = self.read_config()
        for cnf in config["recipients"]:
            if cnf["id"] == new.id:
                cnf = new.to_dict()
                break
        else:
            config["recipients"].append(new.to_dict())
        self.write_config(config)

    def add_recipient(self, message: Message) -> None:
        flags = message.content.split(',')
        user = Recipient(message.sender, message.interface.value, "falling" in flags, "rising" in flags, "bell" in flags)
        self.recipients.append(user)
        self.add_recipient_to_config(user)

if __name__ == "__main__":
    if not path.exists(path.join(ROOT, "data", "api.cfg")):
        name = input("Set the name of the application: ")
        key = input("Insert the key from the bot: ")
        ip = input("Set the IP address of the bot: ")
        port = int(input("Set the port number of the bot: "))
        API.create_config(name, key, ip, port, path.join(ROOT, "data", "api.cfg"))
    bell = Bell(path.join(ROOT, "data", "config.cfg"))
    bell.start()
    try:
        while True:
            if not bell.is_alive():
                bell.logger.error("Bell died!")
                bell.logger.debug("Restarting")
                bell.restart()
            sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        bell.stop()
