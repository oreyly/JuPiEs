from dataclasses import dataclass
from io import TextIOWrapper
import threading
import queue
from datetime import datetime
import os
import sys
import atexit

from typing import Any

from Errors import ERROR_CODES
from LogLevel import LOG_LEVEL
from Utils import Utils

class Logger:
    @dataclass
    class LogEntry:
        Time: datetime
        Caller: type[Any]
        Message: str
        LogLevel: LOG_LEVEL
    
    _logFile: TextIOWrapper | None = None
    _queue: queue.Queue[LogEntry | None] = queue.Queue()
    _running: bool = False
    _workerThread: threading.Thread | None = None
    _initialized = False
    
    _printLock: threading.Lock

    @staticmethod
    def init(logFilePath: str):
        if Logger._initialized:
            return False
        
        try:
            Logger._logFile = open(logFilePath, "a", encoding="utf-8")
        except Exception as e:
            print(f"Nelze vytvořit logovací soubor: {e}")
            return False

        Logger._printLock = threading.Lock()
        Logger._running = True
        Logger._initialized = True
        Logger._workerThread = threading.Thread(target=Logger.LogLoop, daemon=True)
        Logger._workerThread.start()
        
        atexit.register(Logger.terminate)

        Logger._logFile.write(f"{'='*10} Začátek relace {'='*10}\n")
        Logger.LogMessage(Logger, f"Logger úspěšně inicializován. Soubor: {os.path.abspath(logFilePath)}")
        return True

    @staticmethod
    def terminate():
        if not Logger._initialized:
            return

        Logger.LogMessage(Logger, "Konec logování")
        Logger._running = False
        Logger._queue.put(None) # Signalizace pro ukončení vlákna
        
        if Logger._workerThread:
            Logger._workerThread.join()

        if Logger._logFile:
            Logger._logFile.write(f"{'='*10} Konec relace {'='*10}\n")
            Logger._logFile.close()
        
        Logger._initialized = False

    @staticmethod
    def LogMessage(caller: type[Any], message: str, level: LOG_LEVEL=LOG_LEVEL.INFO, send_to_stdout: bool=True):
        timeOfMessage = datetime.now()
        if not Logger._running:
            return
        
        if send_to_stdout:
            with Logger._printLock:
                print(message)

        Logger._queue.put(Logger.LogEntry(timeOfMessage, caller, message, level))

    @staticmethod
    def LogError(caller: type[Any], errorCode: ERROR_CODES, params: list[Any] = [], logLevel: LOG_LEVEL=LOG_LEVEL.ERROR, sendToStderr: bool=True):
        timeOfError = datetime.now()
        message = str(errorCode).format(*params)
        if not Logger._running:
            return
        
        if(not Utils.CheckTemplateParams(str(errorCode), params)):
            Logger.LogError(Logger, ERROR_CODES.BAD_PARAMETERS_FOR_ERROR, [errorCode.name, params])
            return
        
        if sendToStderr:
            with Logger._printLock:
                print(message, file=sys.stderr)

        Logger._queue.put(Logger.LogEntry(timeOfError, caller, message, logLevel))

    @staticmethod
    def LogLoop():
        while True:
            item = Logger._queue.get()
            if item is None and not Logger._running:
                while not Logger._queue.empty():
                    entry = Logger._queue.get()
                    if entry:
                        Logger.WriteToFile(entry)
                break
            
            if item:
                Logger.WriteToFile(item)
            Logger._queue.task_done()

    @staticmethod
    def WriteToFile(logEntry: LogEntry):
        if(not Logger._logFile):
            return
        
        timeStr = logEntry.Time.strftime("%H:%M:%S")
        
        Logger._logFile.write(f"[{logEntry.LogLevel.value}] [{timeStr}] [{logEntry.Caller.__name__}] {logEntry.Message}\n")
        Logger._logFile.flush()
