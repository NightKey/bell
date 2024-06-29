from socket import socket, AF_INET, SOCK_STREAM, timeout
from smdb_logger import Logger
from threading import Thread, Lock, Event
from os import devnull
from sys import stdout, __stdout__
from typing import Dict, Callable

is_stdout_devnull = False

def blockPrint() -> None:
    global stdout
    global is_stdout_devnull
    stdout = open(devnull, 'w')
    is_stdout_devnull = True


def enablePrint() -> None:
    global stdout
    global is_stdout_devnull
    if (is_stdout_devnull):
        stdout.close()
        stdout = __stdout__
        is_stdout_devnull = False

class Client:
    def __init__(self, ip: str, port: int, logger: Logger = None) -> None:
        self.logger = logger
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.connected = False
        self.connection_error_sent = False
        self.target_ip = ip
        self.target_port = port
        self.stop_event = Event()
        self.read_lock = Lock()
        self.loop_thread: Thread = None
        self.handlers: Dict[str, Callable[[], None]] = {}
        self.ready_event = Event()

    def start(self) -> None:
        if self.logger is not None: self.logger.info("Starting client")
        self.create_connection()
        self.loop_thread = Thread(target=self.__loop)
        self.loop_thread.name = "Connector Loop Thread"
        self.loop_thread.start()

    def create_connection(self):
        self.ready_event.clear()
        try:
            if self.socket.connect_ex((self.target_ip, self.target_port)) != 0:
                self.socket.close()
                self.socket.detach()
                self.socket = socket(AF_INET, SOCK_STREAM)
                self.socket.connect((self.target_ip, self.target_port))
            if self.logger is not None: self.logger.debug(f"Client connected to {self.target_ip}:{self.target_port}")
            self.socket.settimeout(2)
            self.connected = True
            self.connection_error_sent = False
        except TimeoutError:
            if self.logger is not None: self.logger.warning("Connection timedout!")
            if not self.connection_error_sent: 
                self.handlers["timeout"]()
                self.connection_error_sent = True
            return
        except OSError as er:
            if self.logger is not None: self.logger.warning(f"OSError: {er}")
            if not self.connection_error_sent: 
                self.handlers["timeout"]()
                self.connection_error_sent = True
            return

    def stop(self) -> None:
        if self.logger is not None: self.logger.info("Stopping client")
        self.stop_event.set()

    def send(self, message: str) -> str:
        while not self.ready_event.is_set():
            self.ready_event.wait(.1)
        if self.logger is not None: self.logger.trace("Aquireing read lock...")
        self.read_lock.acquire()
        if self.logger is not None: self.logger.debug(f"Sending data: {message}")
        try:
            response = None
            while response is None or response == "Not a valid command":
                if self.connected:
                    self.__send(message)
                    response = self.__retrive()
                else:
                    self.create_connection()
                    self.stop_event.wait(.1)
                if self.stop_event.is_set():
                    return response
            if self.logger is not None: self.logger.debug(f"Response: {response}")
            return response
        finally:
            self.read_lock.release()
            if self.logger is not None: self.logger.trace("lock released")

    def __send(self, msg: str) -> None:
        self.socket.send(msg.encode(encoding="utf-8"))
        self.socket.send(bytes(0))

    def __retrive(self, faile_on_timeout: bool = True) -> str:
        ret = b""
        while True:
            try:
                blockPrint()
                while (data := self.socket.recv(1)) != b'\x00':
                    ret += data
                enablePrint()
                return ret.decode()
            except timeout:
                if faile_on_timeout: 
                    enablePrint()
                    return None
                continue
            except ConnectionResetError:
                enablePrint()
                self.connected = False
                return None
            except Exception as ex:
                enablePrint()
                print(f"[_retrive exception]: {ex}")
                raise ex

    def __loop(self):
        counter = 0
        while not self.stop_event.is_set():
            while not self.connected:
                self.create_connection()
            while self.read_lock.locked():
                self.stop_event.wait(1)
            self.read_lock.acquire()
            message = self.__retrive()
            self.read_lock.release()
            if message is not None and message in self.handlers.keys():
                self.handlers[message]()
            elif message is not None and self.ready_event.is_set() and self.logger is not None: self.logger.debug(f"Bad message: {message}")
            if not self.ready_event.is_set() and message is None: counter += 1
            if counter >= 5:
                self.ready_event.set()
                counter = 0
            self.stop_event.wait(.5 if self.ready_event.is_set() else .1)

    def add_handler(self, callback: Callable[[], None], message: str) -> None:
        self.handlers[message] = callback
