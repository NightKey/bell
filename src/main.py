from datetime import datetime
from smdb_api import API, Message, Interface, Privilege
from smdb_logger import Logger, LEVEL
from typing import Dict, List, Any, Union
from smdb_web_server import HTMLServer, UrlData
from threading import Thread, Event
from time import sleep
from os import path, mkdir
from data import SensorData, Recepient, Thresholds, temperature_to_hue, translate
from connector import Client
from slope_detector import Direction, detect_slope
from json import load, dumps, dump, JSONDecodeError

ROOT = path.dirname(path.dirname(__file__))
TEMPLATES = {"index": "PATH|data/template/index.html", "chart": "PATH|data/template/chart.html"}
STATIC = {"styles": "PATH|data/static/styles.css", "scripts": "PATH|data/static/scripts.js", "colorschema": "PATH|data/static/colorschema.css", "favicon":"PATH|data/static/favicon.svg", "charts": "PATH|data/static/charts.js"}

class Bell:
    def __init__(self, config_paht: str):
        self.config_path = config_paht
        config = self.read_config()
        self.logger = Logger("Bell.log", log_folder=path.join(ROOT, "data"), level=LEVEL.INFO, use_caller_name=True)
        self.api = API.from_config(path.join(ROOT, "data", "api.cfg"))
        self.web_server = HTMLServer(config["SERVER"]["host"], config["SERVER"]["port"], ROOT, logger=self.logger)
        self.sensor_history: List[SensorData] = []
        self.request_time = config["request_time"]
        self.recepients: List[Recepient] = [Recepient.from_json(x) for x in config["recepients"]]
        self.bell_connector = Client(config["BELL"]["host"], config["BELL"]["port"], self.logger)
        self.bell_connector.add_handler(self.bell_callback, "Bell")
        self.bell_connector.add_handler(self.bell_timeout_callback, "timeout")
        self.stop_event = Event()
        self.main_thread: Thread = None
        self.last_save = datetime.now()

    def prepare_webpage(self):
        self.web_server.add_url_rule("/", self.__index)
        self.web_server.add_url_rule("/get", self.__get_weather)
        self.web_server.add_url_rule("/save", self.__save)
        self.web_server.add_url_rule("/chart", self.__chart)
    
    def prepare_api(self):
        self.api.create_function("AddRecepient", "Adds recepient to the bell and weather alerts. At least one argument is required, if multiple is present separate them by ','!\nUsage: &AddRecepient [falling|rising|bell]\nCategory: NETWORK", self.add_recepient, privilege=Privilege.OnlyAdmin, needs_arguments=True)

    def save_datapoints(self) -> None:
        if not path.exists(path.join(ROOT, "data", "powerbi")):
            mkdir(path.join(ROOT, "data", "powerbi"))
        with open(path.join(ROOT, "data", "powerbi", f"data_history{datetime.now().strftime(r'%Y.%m.%d')}.json"), "w") as fp:
            fp.writelines(dumps([item.to_dict() for item in self.sensor_history]))

    def __save(self, _) -> str:
        self.save_datapoints()
        return "Done"

    def __get_weather(self, data: UrlData) -> str:
        if ("current" in data.query):
            self.fetch_data()
            self.sensor_history.sort(reverse=True)
            return self.sensor_history[0].to_json()
        elif ("history" in data.query):
            if (len(self.sensor_history) >= 5):
                self.sensor_history.sort(reverse=True)
                data = {"items": [item.to_dict() for item in self.sensor_history[1:5]], "refference": self.sensor_history[5].to_dict()}
            else:
                data = {}
            return dumps(data)
        elif ("chart" in data.query):
            self.sensor_history.sort(reverse=True)
            return dumps({"items": [it.to_dict(True) for it in self.sensor_history]})

    def __chart(self, _) -> str:
        return self.web_server.render_template_file("chart", page_title="Charts")

    def __index(self, _) -> str:
        current_data = self.sensor_history[0]
        temperatureHue = int(temperature_to_hue(current_data.temperature))
        heatIndexHue = int(temperature_to_hue(current_data.heat_index))
        pressureP = int(translate(current_data.pressure / 100, 980, 1020, 0, 100))
        return self.web_server.render_template_file(
            "index",
            page_title="Weather",
            humidity=str(round(current_data.humidity, 1)),
            humidityp=str(int(current_data.humidity)),
            humidityless="" if current_data.humidity > 50 else " less",
            heatindex=str(round(current_data.heat_index, 1)),
            heatindexp=str(heatIndexHue),
            temperature=str(round(current_data.temperature, 1)),
            temperaturep=str(temperatureHue),
            pressure=str(round(current_data.pressure / 100, 1)),
            pressurep=str(pressureP),
            pressureless="" if pressureP > 50 else " less",
            temperature_unit=current_data.temperature_unit
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
        if (self.request_time > 10):
            Thread(target=self.hearth_beat, name="Bell Hearth Beat thread").start()

    def hearth_beat(self):
        while not self.stop_event.is_set():
            self.bell_connector.send("ping")
            self.stop_event.wait(10)

    def stop(self):
        self.api.close("Program terminating")
        self.web_server.stop()
        self.bell_connector.stop()
        self.stop_event.set()
    
    def bell_timeout_callback(self):
        for person in self.recepients:
            if not person.alert_on_bell:
                return
            self.api.send_message("Bell is not connected!", Interface(person.interface), person.id)

    def bell_callback(self):
        if self.logger is not None: self.logger.trace("Bell rang")
        for person in self.recepients:
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
            sensorData = SensorData.from_json(response)
            if (len(self.sensor_history) > 0):
                self.sensor_history.sort(reverse=True)
                sensorData.set_delta_compared_to(self.sensor_history[0])
            else:
                sensorData.set_delta_compared_to(None)
            self.sensor_history.insert(0, sensorData)
            if (datetime.now() - self.last_save).total_seconds() > 86400:
                self.save_datapoints()
                self.sensor_history = [sensorData]
                self.last_save = datetime.now()
        except JSONDecodeError:
            if self.logger is not None: self.logger.warning(f"Response was not JSON deserializable: `{response}`")

    def main_loop(self):
        message_sent = False
        while not self.stop_event.is_set():
            try:
                self.fetch_data()
                (pressure_dir, temperature_dir, humidity_dir) = self.get_trends()
                if (pressure_dir == Direction.FALLING and not message_sent):
                    for person in self.recepients:
                        if (not person.alert_on_falling): continue
                        self.api.send_message("Pressure is falling rapidly!", Interface(person.interface), person.id)
                    message_sent = True
                elif (pressure_dir == Direction.RISING and not message_sent):
                    for person in self.recepients:
                        if (not person.alert_on_rising): continue
                        self.api.send_message("Pressure is rising rapidly!", Interface(person.interface), person.id)
                    message_sent = True
                elif (pressure_dir == Direction.STATIC):
                    message_sent = False
                self.stop_event.wait(self.request_time)
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt!")
                self.stop()
            except Exception as ex:
                self.logger.error(f"Exception: {ex}")

    def read_config(self) -> Dict[str, Union[List[Dict[str, Any]], Dict[str, Any]]]:
        if not path.exists(self.config_path):
            self.write_config({"request_time": 60, "SERVER": { "host": "LOCAL IP", "port": 6969 }, "BELL": { "host": "ESP IP", "port": 6900 }, "recepients": []})
            raise FileNotFoundError("Config file not found. Please fill in the newly created config file!")
        config = {}
        with open(self.config_path, "r") as fp:
            config = load(fp)
        return config

    def write_config(self, config: Dict[str, Union[List[Dict[str, Any]], Dict[str, Any]]]) -> None:
        with open(self.config_path, "w") as fp:
            dump(config, fp)

    def add_recepient_to_config(self, new: Recepient) -> None:
        config = self.read_config()
        for cnf in config["recepients"]:
            if cnf["id"] == new.id:
                cnf = new.to_dict()
                break
        else:
            config["recepients"].append(new.to_dict())
        self.write_config(config)

    def add_recepient(self, message: Message) -> None:
        flags = message.content.split(',')
        user = Recepient(message.sender, message.interface.value, "falling" in flags, "rising" in flags, "bell" in flags)
        self.recepients.append(user)
        self.add_recepient_to_config(user)        

if __name__ == "__main__":
    if (not path.exists(path.join(ROOT, "data", "api.cfg"))):
        name = input("Set the name of the application: ")
        key = input("Insert the key from the bot: ")
        ip = input("Set the IP address of the bot: ")
        port = int(input("Set the port number of the bot: "))
        API.create_config(name, key, ip, port, path.join(ROOT, "data", "api.cfg"))
    bell = Bell(path.join(ROOT, "data", "config.cfg"))
    bell.start()
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        bell.stop()
