import threading
import queue
import time
from datetime import datetime
from enum import Enum
import os

class LogLevel(Enum):
    INFO = "INFO"
    ERROR = "ERROR"
    WARNING = "WARNING"

class Logger:
    _log_file = None
    _queue = queue.Queue()
    _running = False
    _worker_thread = None
    _initialized = False

    @staticmethod
    def init(log_file_path):
        if Logger._initialized:
            return False
        
        try:
            Logger._log_file = open(log_file_path, "a", encoding="utf-8")
        except Exception as e:
            print(f"Nelze vytvořit logovací soubor: {e}")
            return False

        Logger._running = True
        Logger._initialized = True
        Logger._worker_thread = threading.Thread(target=Logger._log_loop, daemon=True)
        Logger._worker_thread.start()

        Logger._log_file.write(f"{'='*10} Začátek relace {'='*10}\n")
        Logger.log_message("Logger", f"Logger úspěšně inicializován. Soubor: {os.path.abspath(log_file_path)}")
        return True

    @staticmethod
    def terminate():
        if not Logger._initialized:
            return

        Logger.log_message("Logger", "Konec logování")
        Logger._running = False
        Logger._queue.put(None) # Signalizace pro ukončení vlákna
        
        if Logger._worker_thread:
            Logger._worker_thread.join()

        if Logger._log_file:
            Logger._log_file.write(f"{'='*10} Konec relace {'='*10}\n")
            Logger._log_file.close()
        
        Logger._initialized = False

    @staticmethod
    def log_message(caller, message, level=LogLevel.INFO, send_to_stdout=True):
        if not Logger._running: return
        if send_to_stdout: print(message)
        Logger._queue.put((datetime.now(), caller, message, level))

    @staticmethod
    def log_error(caller, error_code_msg, level=LogLevel.ERROR, send_to_stderr=True):
        if not Logger._running: return
        if send_to_stderr: import sys; print(error_code_msg, file=sys.stderr)
        Logger._queue.put((datetime.now(), caller, error_code_msg, level))

    @staticmethod
    def _log_loop():
        while True:
            item = Logger._queue.get()
            if item is None and not Logger._running:
                # Zpracovat zbytek fronty před ukončením
                while not Logger._queue.empty():
                    entry = Logger._queue.get()
                    if entry: Logger._write_to_file(*entry)
                break
            
            if item:
                Logger._write_to_file(*item)
            Logger._queue.task_done()

    @staticmethod
    def _write_to_file(timestamp, caller, message, level):
        ts_str = timestamp.strftime("%H:%M:%S")
        log_line = f"[{level.value}] [{ts_str}] [{caller}] {message}\n"
        Logger._log_file.write(log_line)
        Logger._log_file.flush()
