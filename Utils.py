import argparse
import functools
import socket
import string
import time
from typing import Any, Callable, Concatenate, Literal, ParamSpec, TypeVar

from Server import Server

P = ParamSpec("P")
R = TypeVar("R")

class Utils:
    @staticmethod
    def CheckRunning(func: Callable[Concatenate[Any, P], R]) -> Callable[Concatenate[Any, P], R | None]:
        @functools.wraps(func)
        def wrapper(self: Any, *args: P.args, **kwargs: P.kwargs) -> R | None:
            if self._running:
                return func(self, *args, **kwargs)
            return None
        
        return wrapper

    @staticmethod
    def CheckTemplateParams(sablona: str, params: list[str]) -> bool:
        iterator = string.Formatter().parse(sablona)
        
        placeholderCount = sum(1 for _, field_name, _, _ in iterator if field_name is not None)
        
        return placeholderCount == len(params)

    @staticmethod
    def UpdateLastEcho(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Pylance strict vyžaduje jasnou definici atributu
            Server.LastEcho = time.monotonic()
            return func(*args, **kwargs)
        return wrapper

    @staticmethod
    def IsValidIp(ip: str) -> bool:
        try:
            socket.gethostbyname(ip)
            return True
        except socket.gaierror:
            return False

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
    
    @staticmethod
    def ParseParams():
        from Logger import Logger
        
        parser = argparse.ArgumentParser(add_help=False)

        parser.add_argument(
        '-h', '--help',
        action='help',
        default=argparse.SUPPRESS,
        help='Zde je váš vlastní text nápovědy'
        )

        parser.add_argument('-i', '--ip', type=Utils.ValidIp, help='IP, kde aplikace naslouchá')
        parser.add_argument('-p', '--port', type=Utils.ValidPort, default=0, help='Port na kterém aplikace naslouchá')
        
        args = parser.parse_args()
        
        address: str | Literal[socket.AddressFamily.AF_INET] = socket.AF_INET
        port: int = 0
        
        if(args.port):
            address = args.address
        else:
            Logger.LogMessage(Utils, f"Nebyla zadána platná ip adresa a bude tedy použita 0.0.0.0")
            
        if(args.port):
            port = args.port
        else:
            Logger.LogMessage(Utils, f"Nebyl zadán platný port a bude tedy použit náhodný")
        
        return address, port
