import threading
import time
import socket
import tkinter as tk
from typing import Callable, Literal
from Errors import ERROR_CODES
import GameLobby
from LoadingOverlay import LoadingOverlay
from Logger import Logger
from Comunicator import Comunicator
from MessageManager import MessageManager
from OPCODE import OPCODE
from Request import IncomingRequest
from RequestManager import RequestManager
from GameLobby import GameLobby

from Server import Server
from Utils import Utils
from connectWindow import ConnectionDialog
from nameWindow import NameDialog

class Program:
    MAX_RECON_ATTEMPTS: int = 2

    _nextProcessFunction: Callable[[IncomingRequest], None] | None
    Comunicaator: Comunicator | None
    MessManager: MessageManager | None
    ReqManager: RequestManager | None
    Running: bool
    
    _onReconect: Callable[[], None] | None
    _reconnectAttempts: int
    
    Loading: LoadingOverlay | None
    
    Root: tk.Tk
    
    CheckerThread: threading.Thread | None

    def __init__(self):
        self._nextProcessFunction = None
        self._onReconect = None
        self.Running = False
        self.CheckerThread = None
        self._reconnectAttempts = 0

    def RegisterProcessingFunction(self, nextProcessFunction: Callable[[IncomingRequest], None]):
        self._nextProcessFunction = nextProcessFunction

    def CouldntReping(self):
        Logger.LogError(Program, ERROR_CODES.PING_CANT_RESPOND)

    def ProcessIncomingMessage(self, incomingRequest: IncomingRequest):
        if(not self.ReqManager):
            Logger.LogError(Program, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        
        if(incomingRequest.DemandMessage.MainPacket.ConnectionID != Server.ConnectionID):
            Logger.LogMessage(Program, f"Zahození zprávy se starým connectionID {incomingRequest.DemandMessage.MainPacket.CreateString()}")
            return
        
        if(not Server.Online):
            Logger.LogMessage(Program, f"Zahození zprávy z offline serveru {incomingRequest.DemandMessage.MainPacket.CreateString()}")
            return
        
        Server.LastEcho = time.monotonic()
        
        match(incomingRequest.DemandMessage.MainPacket.Opcode):
            case OPCODE.PING:
                self.ReqManager.SendResponse(OPCODE.I_SEE_YOU, [], self.CouldntReping)
                Server.LastEcho = time.monotonic()
            case _:
                if(self._nextProcessFunction):
                    self._nextProcessFunction(incomingRequest)
                else:
                    raise Exception("Nelze zpracovat")
    
    def Leave(self) -> None:
        Logger.LogMessage(Program, "lýv")
        if(not self.ReqManager):
            Logger.LogError(GameLobby, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        
        self.ReqManager.CreateDemand(OPCODE.AM_LEAVING, [], self.ServerNotKnowAmLeaving, self.ServerAcknoledgedMyLeft,OPCODE.YOU_LEFT)
    
    def ServerNotKnowAmLeaving(self):
        self.Root.destroy()
    
    @Utils.UpdateLastEcho
    def ServerAcknoledgedMyLeft(self, responseParams: list[str]):
        self.Root.destroy()

    def ServerChecker(self):
        while(self.Running):
            time.sleep(1)
            now = time.monotonic()
            if(Server.Online and now - Server.LastEcho < 10):
                continue

            if(Server.Online):
                self.DisableServer()
                break

    def EnableServer(self):
        self.Running = True
        self._reconnectAttempts = 0
        self.CheckerThread = threading.Thread(target=self.ServerChecker ,daemon=True)
        self.CheckerThread.start()

    def DisableServer(self):
        Server.Online = False
        self.Loading = LoadingOverlay(self.Root, "Připojování")
        self.TryToReconect()
        
    def TryToReconect(self):
        self._reconnectAttempts += 1
        
        if(self._reconnectAttempts > self.MAX_RECON_ATTEMPTS):
            self.Root.withdraw()
            self.Root = tk.Tk()
            self.ConnectToServer()
            return
            
        if(not self.ReqManager):
            Logger.LogError(Program, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        
        self.ReqManager.CreateDemand(OPCODE.RECON, [str(Server.MyId)], self.ReconnectFailed, self.ReconnectSucceded, OPCODE.RECON_AS)
        
    def ReconnectFailed(self):
        Logger.LogError(Program, ERROR_CODES.FAILED_TO_RECONNECT)
        self.TryToReconect()
    
    def ReconnectSucceded(self, responseParams: list[str]):
        if(Server.Online):
            Logger.LogError(Program, ERROR_CODES.ALREAD_CONNECTED)
            return
        
        if(not self.Loading):
            Logger.LogError(Program, ERROR_CODES.OBJECT_NOT_INITIALIZED, [LoadingOverlay.__name__])
            return
        
        Server.Online = True
        Server.ConnectionID = int(responseParams[0])
        Server.LastEcho = time.monotonic()
        self.Loading.stop()
        Logger.LogMessage(Program, "Klient se úspěšně připojil zpátky na server")
        self.EnableServer()
        self.OnReconect()
    
    def RegisterOnReconnect(self, onReconnect: Callable[[], None]):
        self._onReconect = onReconnect
    
    def UnregisterOnReconnect(self):
        self._onReconect = None
    
    def OnReconect(self):
        if(self._onReconect):
            self._onReconect()
        
    def SetupCom(self, address: str | Literal[socket.AddressFamily.AF_INET], port: int =0):
        comunicator = Comunicator(address,port)
        
        if(not comunicator.Initialized):
            return False, None, None, None
        
        msgManager = MessageManager()
        msgManager.ConnectToComunicator(comunicator, 5000, 1)

        reqManager = RequestManager(5000)
        reqManager.ConnectToMessageManager(msgManager)
        reqManager.RegisterProcessingFunction(self.ProcessIncomingMessage)
        
        return True, comunicator, msgManager, reqManager
    
    def ConnectToServer(self):
        dialog = ConnectionDialog(self)
        dialog.Open()

    def RegisterName(self):
        dialog = NameDialog(self)
        dialog.Open()

    def OpenLobby(self, reconected: bool):
        gl = GameLobby(self)
        gl.Open(reconected)
        
    
    def main(self):
        Logger.init("client_log3.txt")
        
        address, port = Utils.ParseParams()
        successInit, self.Comunicaator, self.MessManager, self.ReqManager = self.SetupCom(address, port)
        
        if(not successInit):
            return
        
        self.Root = tk.Tk()

        self.ConnectToServer()
        """
        if( not self.ConnectToServer()):
            return
        print("XD")
        if( not self.RegisterName()):
            return
        
        gl = GameLobby(self)
        gl.Open()"""
    
if __name__ == "__main__":
    program = Program()
    program.main()
