import argparse
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
import sys

class Program:
    _nextProcessFunction: Callable[[IncomingRequest], None] | None
    Comunicaator: Comunicator | None
    MessManager: MessageManager | None
    ReqManager: RequestManager | None
    Running: bool
    
    Loading: LoadingOverlay | None
    
    Root: tk.Tk
    
    CheckerThread: threading.Thread | None

    def __init__(self):
        self._nextProcessFunction = None
        self.Running = False
        self.CheckerThread = None

    def RegisterProcessingFunction(self, nextProcessFunction: Callable[[IncomingRequest], None]):
        self._nextProcessFunction = nextProcessFunction

    def SetupCom(self, address: str | Literal[socket.AddressFamily.AF_INET], port: int =0):
        comunicator = Comunicator(address,port)
        
        if(not comunicator.Initialized):
            return False, None, None, None
        
        msgManager = MessageManager()
        msgManager.ConnectToComunicator(comunicator, 2000, 1)

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

    def OpenLobby(self):
        gl = GameLobby(self)
        gl.Open()
    
    def CouldntReping(self):
        Logger.LogError(Program, ERROR_CODES.PING_CANT_RESPOND)

    def ProcessIncomingMessage(self, incomingRequest: IncomingRequest):
        if(not self.ReqManager):
            Logger.LogError(Program, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        
        #if(not Server.Online and incomingRequest.DemandMessage.MainPacket.Opcode != OPCODE.RECONECTED):
        #    Logger.LogMessage(Program, f"Zahození zprávy z offline serveru {incomingRequest.DemandMessage.MainPacket.CreateString()}")
        #    return
        
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
    
    def ServerAcknoledgedMyLeft(self, responseParams: list[str]):
        self.Root.destroy()

    def ServerChecker(self):
        while(self.Running):
            time.sleep(1)
            now = time.monotonic()
            if(Server.Online and now - Server.LastEcho < 5):
                continue
            
            if(Server.Online):
                self.DisableServer()
            
            self.TryToReconect()

    def TryToReconect(self):
        if(not self.ReqManager):
            Logger.LogError(Program, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        
        self.ReqManager.CreateDemand(OPCODE.RECONECT, [str(Server.MyId)], self.ReconnectFailed, self.ReconnectSucceded, OPCODE.RECONECTED)
        
    def ReconnectFailed(self):
        Logger.LogError(Program, ERROR_CODES.FAILED_TO_RECONNECT)
        
    def ReconnectSucceded(self, responseParams: list[str]):
        if(Server.Online):
            return
        
        Server.Online = True
        Server.LastEcho = time.monotonic()
        Logger.LogMessage(Program, "Klient se úspěšně připojil zpátky na server")
    
    def DisableServer(self):
        Server.Online = False
        self.Loading = LoadingOverlay(self.Root, "Připojování")
    
    @staticmethod
    def ValidIp(ip: str):
        return ip if Utils.IsValidIp(ip) else None
    
    @staticmethod
    def ValidPort(port: str):
        p: int
        try:
            p = int(port)
        except ValueError:
            return None
        
        if(p < 0 or p > 65535):
            return None
        
        return p
    
    def main(self):
        parser = argparse.ArgumentParser(add_help=False)

        parser.add_argument(
        '-h', '--help',
        action='help',
        default=argparse.SUPPRESS,
        help='Zde je váš vlastní text nápovědy'
    )

        parser.add_argument('-i', '--ip', type=Program.ValidIp, help='IP, kde aplikace naslouchá')
        parser.add_argument('-p', '--port', type=Program.ValidPort, default=0, help='Port na kterém aplikace naslouchá')
        
        args = parser.parse_args()
        
        Logger.init("client_log2.txt")
        address: str | Literal[socket.AddressFamily.AF_INET] = socket.AF_INET
        port = 0
        
        if(args.port):
            address = args.address # type: ignore
        else:
            Logger.LogMessage(Program, f"Nebyla zadána platná ip adresa a bude tedy použita 0.0.0.0")
            
        if(args.port):
            port = args.port
        else:
            Logger.LogMessage(Program, f"Nebyl zadán platný port a bude tedy použit náhodný")
            
        
        self.Root = tk.Tk()
        
        if(len(sys.argv) > 1):
            port = int(int(sys.argv[2]))

        successInit, self.Comunicaator, self.MessManager, self.ReqManager = self.SetupCom(address, port)
        if(not successInit):
            return
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
