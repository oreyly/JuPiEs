from __future__ import annotations
import itertools
from enum import IntEnum
from typing import List

from OPCODE import OPCODE

class ORIGIN(IntEnum):
    SERVER = 0
    CLIENT = 1

class Packet:
    _idGenerator = itertools.count(1)
    _delimiter = '-'
    
    Id: int
    ClientId: int
    RequestOrigin: ORIGIN
    Opcode: OPCODE
    Parameters: list[str]
    IsValid: bool

    def __init__(self, id: int | None = None, targetId: int = 0, connectionID: int = 0, requestOrigin: ORIGIN = ORIGIN.CLIENT, opcode: OPCODE = OPCODE.ACK, params: List[str] | None = None, isValid: bool = True):
        self.Id = next(self._idGenerator) if id is None else id
        self.ClientId = targetId
        self.ConnectionID = connectionID
        self.RequestOrigin = requestOrigin
        self.Opcode = opcode
        self.Parameters = params or []
        self.IsValid = isValid

    @staticmethod
    def FromString(message: str) -> Packet:
        parts = message.split(Packet._delimiter)
        
        if(not (len(parts) >= 5 and parts[0].isdigit()  and parts[1].isdigit() and parts[2].isdigit() and parts[3].isdigit() and parts[4].isdigit() and (int(parts[3]) in ORIGIN) and (int(parts[4]) in OPCODE))):
            return Packet(isValid=False)
        
        return Packet(id=int(parts[0]), targetId=int(parts[1]), connectionID=int(parts[2]), requestOrigin=ORIGIN(int(parts[3])), opcode=OPCODE(int(parts[4])), params=parts[5:])
    
    def CreateString(self) -> str:
        baseStr = f"{self.Id}{self._delimiter}{self.ClientId}{self._delimiter}{self.ConnectionID}{self._delimiter}{int(self.RequestOrigin)}{self._delimiter}{int(self.Opcode)}"
        if not self.Parameters:
            return baseStr
        
        return f"{baseStr}{self._delimiter}{self._delimiter.join(self.Parameters)}"
