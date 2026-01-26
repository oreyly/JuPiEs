import argparse
import socket
import tkinter as tk
from typing import Callable, Literal
from Errors import ERROR_CODES
import GameLobby
from Logger import Logger
from Comunicator import Comunicator
from MessageManager import MessageManager
from OPCODE import OPCODE
from Request import IncomingRequest
from RequestManager import RequestManager
from GameLobby import GameLobby

from Utils import Utils
from connectWindow import ConnectionDialog
from nameWindow import NameDialog
import sys

class Program:
    _nextProcessFunction: Callable[[IncomingRequest], None] | None
    Comunicaator: Comunicator | None
    MessManager: MessageManager | None
    ReqManager: RequestManager | None
    
    Root: tk.Tk

    def __init__(self):
        self._nextProcessFunction = None

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

    def ProcessIncomingMessage(self, incomingRequest: IncomingRequest):
        match(incomingRequest.DemandMessage.MainPacket.Opcode):
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
