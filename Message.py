from __future__ import annotations
import threading
from typing import Callable, TYPE_CHECKING

from Errors import ERROR_CODES
from LogLevel import LOG_LEVEL
from Logger import Logger
from Utils import Utils

# Importujeme pouze pro statickou analýzu, za běhu se tento blok nevykoná
if TYPE_CHECKING:
    from Packet import Packet
    from MessageManager import MessageManager

class IncomingMessage:
    def __init__(self, packet: Packet):
        self.MainPacket = packet

class OutgoingMessage:
    MainPacket: Packet
    
    _running: bool
    _finished: threading.Event
    
    _timeout: float
    _onTimeout: Callable[[], None]
    
    _maxAttempts: int
    _attempts: int
    
    _messageManager: MessageManager | None
    
    _worker: threading.Thread | None
    
    def __init__(self, packet: Packet, onTimeout: Callable[[], None]):
        self.MainPacket = packet
        self._onTimeout = onTimeout
        self._attempts = 0
        
        self.Finished = False
        
        self._running = False
        self._finished = threading.Event()
        
        self._messageManager = None
        
        self._worker = None

    def RegisterMessageManager(self, messageManager: MessageManager, timeout: int, maxAttempts: int):
        if(self._messageManager):
            Logger.LogError(OutgoingMessage, ERROR_CODES.ALREAD_REGISTERED)
            return
        
        self._timeout = timeout / 1000.0
        self._maxAttempts = maxAttempts
        self._message_manager = messageManager

    def OnMessageSent(self):
        self._attempts += 1
        
        self._running = True
        self._finished = threading.Event()
        
        self._worker = threading.Thread(target=self.WaitForAck, daemon=True)
        self._worker.start()

    @Utils.CheckRunning
    def Finish(self):
        self._finished.set()

    def WaitForAck(self): 
        while not self._finished.is_set():
            if self._finished.wait(self._timeout):
                if(not self._running):
                    return
                
            if self._attempts >= self._maxAttempts:
                break
            
            self._attempts += 1
            
            self._message_manager.SendPacket(self.MainPacket)
                
        if not self._finished.is_set():
            Logger.LogError(OutgoingMessage, ERROR_CODES.MESSAGE_TIMEOUT, [self.MainPacket.CreateString()], LOG_LEVEL.WARNING)
            self._onTimeout()
            return
