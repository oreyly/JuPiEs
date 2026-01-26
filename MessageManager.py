import threading
import queue
import time
from typing import Callable
from Comunicator import Comunicator
from Message import IncomingMessage, OutgoingMessage
from OPCODE import OPCODE
from Packet import Packet, ORIGIN
from Logger import Logger
from Errors import ERROR_CODES
from Utils import Utils

class MessageManager:
    CLEANER_SLEEP_SEC = 1.0
    HISTORY_LIMIT_SEC = 60.0

    _running: threading.Event
    
    _messageTimeout: int
    _maxMessageAttempts: int
    
    _comunicator: Comunicator | None
    
    _processingFunction: Callable[[IncomingMessage], None] | None
    
    _outgoingMessages: dict[int, OutgoingMessage]
    
    _incomingMessages: dict[int, float]
    
    _finishedIdTimesList: dict[int,float]

    _arrivedMessages: queue.Queue[str | None]
    
    _cleaningWorker: threading.Thread | None
    _messageWorker: threading.Thread | None
    
    _lockFinished: threading.Lock
    
    _lockIncoming: threading.Lock
    _lockOutgoing: threading.Lock
    
    def __init__(self):
        self._running = threading.Event()
        self._messageTimeout = 50
        self._maxMessageAttempts = 3
        
        self._comunicator: Comunicator | None = None
        self._processingFunction: Callable[[IncomingMessage], None] | None = None
        
        self._outgoingMessages = {}
        self._incomingMessages = {}
        self._arrivedMessages = queue.Queue()
        
        self._finishedIdTimesList = {}
        
        self._lockOutgoing = threading.Lock()
        self._lockIncoming = threading.Lock()
        self._lockFinished = threading.Lock()

        self._messageWorker: threading.Thread | None = None
        self._cleaningWorker: threading.Thread | None = None
        Logger.LogMessage(MessageManager, "Vytvořen MessageManager.")

    def ConnectToComunicator(self, comunicator: Comunicator, messageTimeout: int, maxMessageAttempts: int):
        if(self._running.is_set()):
            Logger.LogError(MessageManager,ERROR_CODES.ALREADY_CONNECTED_MANAGER)
            return
        
        self._message_timeout = messageTimeout
        self._max_attempts = maxMessageAttempts
        
        self._running.set()
        
        self._cleaningWorker = threading.Thread(target=self.CleaningLoop, daemon=True)
        self._cleaningWorker.start()
        self._messageWorker = threading.Thread(target=self.MainLoop, daemon=True)
        self._messageWorker.start()
        
        self._comunicator = comunicator
        self._comunicator.RegisterReceiver(self.OnStringRecieve)
        
        Logger.LogMessage(MessageManager,"MessageManager připojen ke komunikátoru.")

    def RegisterProcessingFunction(self, processingFunction: Callable[[IncomingMessage], None]):
        if self._processingFunction:
            Logger.LogError(MessageManager, ERROR_CODES.ALREAD_REGISTERED)
            
        self._processingFunction = processingFunction

    @Utils.CheckRunning
    def SendMessage(self, outgoingMessage: OutgoingMessage):
        with self._lockOutgoing:
            outgoingMessage.RegisterMessageManager(self, self._message_timeout, self._max_attempts)
            self._outgoingMessages[outgoingMessage.MainPacket.Id] = outgoingMessage
            self.SendPacket(outgoingMessage.MainPacket)
            outgoingMessage.OnMessageSent()
    
    @Utils.CheckRunning
    def SendPacket(self, packet: Packet):
        if(not self._comunicator):
            Logger.LogError(MessageManager, ERROR_CODES.OBJECT_NOT_INITIALIZED, [Comunicator])
            return
                    
        self._comunicator.Send(packet.CreateString())

    def CleaningLoop(self):
        while self._running:
            self.CleanFinished()
            time.sleep(self.CLEANER_SLEEP_SEC)
            
        self.CleanFinished()

    def CleanFinished(self):
        now = time.time()
        idToPop: list[int] = []
        with self._lockFinished:
            for id, finTime in self._finishedIdTimesList.items():
                if(now - finTime > self.HISTORY_LIMIT_SEC):
                    idToPop.append(id)

            for id in idToPop:
                self._finishedIdTimesList.pop(id)
        
        idToPop.clear()
        with self._lockIncoming:
            for id, finTime in self._incomingMessages.items():
                if(now - finTime > self.HISTORY_LIMIT_SEC):
                    idToPop.append(id)

            for id in idToPop:
                self._incomingMessages.pop(id)
    

    @Utils.CheckRunning
    def OnStringRecieve(self, messageStr: str):
            self._arrivedMessages.put(messageStr)

    def MainLoop(self):
        while self._running:
                message = self._arrivedMessages.get()
                
                if(message == None):
                    return
                
                packet = Packet.FromString(message)
                if not packet.IsValid:
                    continue

                if packet.Opcode == OPCODE.ACK:
                    with self._lockOutgoing, self._lockFinished:
                        if packet.Id in self._outgoingMessages:
                            msg = self._outgoingMessages.pop(packet.Id)
                            self._finishedIdTimesList[packet.Id] = time.time()
                            Logger.LogMessage(MessageManager, f"Potvrzena zpráva {msg.MainPacket.CreateString()}")
                            msg.Finish()
                    continue
                
                incommingMessage = IncomingMessage(packet)
                self.ConfirmReceiving(incommingMessage)
                
                with self._lockIncoming, self._lockFinished:
                    if(incommingMessage.MainPacket.Id in self._incomingMessages):
                        continue
                    
                    self._incomingMessages[packet.Id] = time.time()
                
                if self._processingFunction:
                    self._processingFunction(incommingMessage)

    def ConfirmReceiving(self, incommingMessage: IncomingMessage):
        self.SendPacket(Packet(id=incommingMessage.MainPacket.Id, targetId=incommingMessage.MainPacket.ClientId,requestOrigin=ORIGIN.SERVER, opcode=OPCODE.ACK))

    def stop(self):
        self._running.clear()
        
        if self._messageWorker:
            self._messageWorker.join()
        if self._messageWorker:
            self._messageWorker.join()
