from __future__ import annotations
import socket
import threading
import queue
from typing import Callable, Literal
from Errors import ERROR_CODES
from Logger import Logger
from Server import Address, Server

class Comunicator:
    _running: threading.Event
    _buffSize: int
    
    _listener: Listener
    
    Initialized: bool
    
    def __init__(self, address: str | Literal[socket.AddressFamily.AF_INET] = socket.AF_INET, port: int = 0):
        self._running = threading.Event()
        self._running.set()
        self._buffSize = 255
        
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.bind(('', port))
            self._sock.settimeout(0.1)
        except Exception:
            Logger.LogError(Comunicator, ERROR_CODES.CANNOT_CREATE_SOCKET)
            self.Initialized = False
            return

        Logger.LogMessage(Comunicator, f"Komunikátor úspěšně inicializován na portu {self._sock.getsockname()[1]}")

        self._listener = self.Listener(self)
        self._sender = self.Sender(self)
        
        self.Initialized = True

    def stop(self):
        if not self._running.is_set():
            return
        
        self._running.clear()
        self._sender.stop()
        self._listener.stop()
        self._sock.close()

    def Send(self, message: str):
        self._sender.send( message)

    def RegisterReceiver(self, recieverFunction: Callable[[str], None]):
        self._listener.RegisterReciever(recieverFunction)

    class Listener:
        _comunicator: Comunicator
        
        _worker: threading.Thread
        _running: bool
        
        _recieverFunction: Callable[[str], None] | None
                
        def __init__(self, comunicator: Comunicator):
            self._comunicator = comunicator
            
            self._recieverFunction = None
            self._worker = threading.Thread(target=self.MainLoop, daemon=True)
            
            self._running = True
            self._worker.start()

        def RegisterReciever(self, recieverFunction: Callable[[str], None]):
            if self._recieverFunction:
                Logger.LogError(Comunicator.Listener, ERROR_CODES.ALREAD_REGISTERED)
                
            self._recieverFunction = recieverFunction

        def stop(self):
            if self._worker.is_alive():
                self._worker.join()

        def MainLoop(self):
            while self._running:
                try:
                    data, _ = self._comunicator._sock.recvfrom(self._comunicator._buffSize)
                    message = data.decode('utf-8')
                    
                    Logger.LogMessage(Comunicator.Listener, f"Přijmuta zpráva: \"{message}\"")
                    
                    if self._recieverFunction:
                        self._recieverFunction(message)
                except (socket.timeout, TimeoutError):
                    continue
                except Exception:
                    if self._running:
                        Logger.LogError(Comunicator.Listener, ERROR_CODES.FATAL_SOCKET)
                    break

    class Sender:
        _running: bool
        
        _comunicator: Comunicator
        
        _worker: threading.Thread
        
        _sendQueue: queue.Queue[str | None]
        
        def __init__(self, comunicator: Comunicator):
            self._running = True
            self._comunicator = comunicator
            self._sendQueue = queue.Queue()
            self._worker = threading.Thread(target=self.MainLoop, daemon=True)
            self._worker.start()

        def send(self, message: str):
            self._sendQueue.put(message)

        def stop(self):
            self._sendQueue.put(None)
            if self._worker.is_alive():
                self._worker.join()

        def MainLoop(self):
            while self._running:
                message = self._sendQueue.get()
                if message is None:
                    break
                
                if( not self.DoSend(message)):
                    return
        
        def DoSend(self, message: str):
            if(not Server.ServerAddress):
                Logger.LogError(Comunicator.Sender, ERROR_CODES.OBJECT_NOT_INITIALIZED, [Address.__name__])
                return
            
            Logger.LogMessage(Comunicator.Sender, f"Odesílání zprávy: \"{ message}\"")
            sent = self._comunicator._sock.sendto(message.encode('utf-8'), (Server.ServerAddress.Ip, Server.ServerAddress.Port))
            
            if(sent < 0):
                Logger.LogError(Comunicator.Sender, ERROR_CODES.FATAL_SOCKET)
                return False
            
            if(sent != len(message)):
                Logger.LogError(Comunicator.Sender, ERROR_CODES.CANNOT_SEND_VIA_SOCKET)
                return False
            
            return True
            
