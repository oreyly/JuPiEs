import itertools
from enum import IntEnum
from dataclasses import dataclass, field
from typing import List, Optional

class Origin(IntEnum):
    SERVER = 0
    CLIENT = 1

class Opcode(IntEnum):
    # Předpokládané hodnoty podle C++ kódu
    ACK = 0 
    # Ostatní opcody definujte zde

class Packet:
    _id_generator = itertools.count(1)
    _delimiter = '-'

    def __init__(self, target_id: int = 0, origin: Origin = Origin.CLIENT, 
                 opcode: Opcode = Opcode.ACK, params: List[str] = None, raw_msg: str = None):
        if raw_msg:
            self._parse_string(raw_msg)
        else:
            self.id = next(self._id_generator)
            self.client_id = target_id
            self.request_origin = origin
            self.opcode = opcode
            self.parameters = params or []
            self.is_valid = True

    def _parse_string(self, message: str):
        parts = message.split(self._delimiter)
        if len(parts) < 4:
            self.is_valid = False
            return

        try:
            self.id = int(parts[0])
            self.client_id = int(parts[1])
            self.request_origin = Origin(int(parts[2]))
            self.opcode = Opcode(int(parts[3]))
            self.parameters = parts[4:]
            self.is_valid = True
        except (ValueError, KeyError):
            self.is_valid = False

    def create_string(self) -> str:
        base = [str(self.id), str(self.client_id), str(int(self.request_origin)), str(int(self.opcode))]
        return self._delimiter.join(base + self.parameters)
