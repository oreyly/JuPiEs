from typing import Callable
import threading
import queue
from Errors import ERROR_CODES
from MessageManager import MessageManager
from Message import IncomingMessage, OutgoingMessage
from OPCODE import OPCODE
from Request import IncomingRequest, OutgoingRequest
from Logger import Logger
from Server import Server
from Packet import ORIGIN, Packet
class RequestManager:
    _timeout: int
    
    _processingFunction: Callable[[IncomingRequest], None] | None
    
    _demandQueue: queue.Queue[OutgoingRequest | None]
    
    _ourDemandsLock: threading.Lock
    _ourDemands: list[OutgoingRequest]
    
    _incomingQueue: queue.Queue[IncomingMessage]
    
    _messageManager: MessageManager | None
    
    _running: threading.Event
    
    _worker: threading.Thread | None

    def __init__(self, timeout: int):
        self._timeout = timeout
        
        self._running = threading.Event()
        
        self._processingFunction = None
        self._messageManager = None
        
        self._demandQueue = queue.Queue()
        self._incomingQueue = queue.Queue()
        
        self._ourDemands = []
        self._ourDemandsLock = threading.Lock()
        
        self._worker = None

    def CreateDemand(self, opcode: OPCODE, params: list[str], onFailure: Callable[[],None], onSuccess:Callable[[list[str]],None], expectedOpcode: OPCODE):
        self._demandQueue.put(OutgoingRequest(opcode, params, self._timeout, onFailure, onSuccess, expectedOpcode))
        
    def SendResponse(self, opcode: OPCODE, params: list[str], onTimeout: Callable[[],None]):
        if(not self._messageManager):
            Logger.LogError(RequestManager, ERROR_CODES.OBJECT_NOT_INITIALIZED, [MessageManager.__name__])
            return
        self._messageManager.SendMessage(OutgoingMessage(Packet(targetId=Server.MyId,requestOrigin=ORIGIN.SERVER,opcode=opcode,params=params), onTimeout))
    
    def RegisterProcessingFunction(self, func: Callable[[IncomingRequest], None]):
        if(self._processingFunction):
            Logger.LogError(RequestManager, ERROR_CODES.ALREAD_REGISTERED)
        
        self._processingFunction = func
        
    def ConnectToMessageManager(self, message_manager: MessageManager):
        self._running.set()
        
        self._messageManager = message_manager
        self._messageManager.RegisterProcessingFunction(self.OnMessageReceive)
        
        self._worker = threading.Thread(target=self.MainLoop, daemon=True)
        self._worker.start()


    def OnMessageReceive(self, incomingMessage: IncomingMessage):
        if(incomingMessage.MainPacket.RequestOrigin == ORIGIN.CLIENT):
            with self._ourDemandsLock:
                for i in range(len(self._ourDemands)):
                    if(self._ourDemands[i].ValidateIncomingMessage(incomingMessage)):
                        self._ourDemands.pop(i)
                        return
                return
        
        if(not self._processingFunction):
            return
        
        if(incomingMessage.MainPacket.RequestOrigin == ORIGIN.SERVER):
            self._processingFunction(IncomingRequest(incomingMessage))
            return
        
        Logger.LogError(RequestManager, ERROR_CODES.UNKNOWN_ORIGIN)

    def MainLoop(self):
        while self._running:
            outgoingRequest = self._demandQueue.get()
            if(outgoingRequest is None):
                break
            
            with self._ourDemandsLock:
                self._ourDemands.append(outgoingRequest)
                
                if(not self._messageManager):
                    Logger.LogError(RequestManager, ERROR_CODES.OBJECT_NOT_INITIALIZED, [MessageManager.__name__])
                    continue
                
                self._messageManager.SendMessage(outgoingRequest.DemandMessage)
                outgoingRequest.OnRequestSend()


    def stop(self):
        self._running.clear()
        if self._worker:
            self._worker.join()
