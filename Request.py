from dataclasses import dataclass
import threading
from typing import Callable, List, Optional
from Message import OutgoingMessage, IncomingMessage
from OPCODE import OPCODE
from Packet import Packet, ORIGIN
from Server import Server
from Utils import Utils

@dataclass
class IncomingRequest:
        DemandMessage: IncomingMessage

class OutgoingRequest:
    _timeout: float
    
    _onFailure: Callable[[],None]
    _onSuccess: Callable[[list[str]],None]
    
    _expectedOpcode: OPCODE
    
    DemandMessage: OutgoingMessage
    
    _responseParams: list[str]
    
    _hasResult: bool
    _waiting: threading.Event
    _worker: threading.Thread | None
    
    _running: bool
    
    def __init__(self, opcode: OPCODE, params: List[str], timeout: int, onFailure: Callable[[], None], onSuccess: Callable[[list[str]], None], expectedOpcode: OPCODE):
        self._running = True
        
        self._timeout = timeout / 1000.0
        self._onFailure = onFailure
        self._onSuccess = onSuccess
        self._expectedOpcode = expectedOpcode
        
        self._waiting = threading.Event()
        self._hasResult = False
        
        p = Packet(targetId=Server.MyId, connectionID=Server.ConnectionID, requestOrigin=ORIGIN.CLIENT, opcode=opcode, params=params)
        self.DemandMessage = OutgoingMessage(p, self.HandleTimeout)
        self._worker: Optional[threading.Thread] = None

    def HandleTimeout(self):
        if not self._hasResult:
            self._waiting.clear()

    @Utils.CheckRunning
    def OnRequestSend(self):
        
        self._worker = threading.Thread(target=self.WaitForResponse, daemon=True)
        self._worker.start()

    def WaitForResponse(self):
        self._waiting.wait(self._timeout)
        self._waiting.set()
        
        
        if(not self._running):
            return
        
        if(not self._hasResult):
            self._hasResult = True
            self._onFailure()
            return
        
        self._onSuccess(self._responseParams)

    @Utils.CheckRunning
    def ValidateIncomingMessage(self, incomingMessage: IncomingMessage) -> bool:
        if self._waiting.is_set():
            return False

        is_valid = (incomingMessage.MainPacket.Opcode == self._expectedOpcode)

        if is_valid:
            self._responseParams = incomingMessage.MainPacket.Parameters
            self._hasResult = True
            self._waiting.set()
        
        return is_valid

    @Utils.CheckRunning
    def stop(self):
        if(not self._running):
            return
        
        self._running = False
        self._waiting.set()
        if self._worker and self._worker.is_alive():
            self._worker.join()
