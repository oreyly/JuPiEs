import functools
import socket
import string
from typing import Any, Callable, Concatenate, ParamSpec, TypeVar

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
    def IsValidIp(ip: str) -> bool:
        try:
            socket.gethostbyname(ip)
            return True
        except socket.gaierror:
            return False
