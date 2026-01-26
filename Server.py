from dataclasses import dataclass

@dataclass(frozen=True)
class Address:
    Ip: str
    Port: int
    
    def __str__(self) -> str:
        return f"{self.Ip}:{self.Port}"

@dataclass
class Server:
    ServerAddress: Address | None = None
    MyId: int = 1
    MyName: str = ""
    
    def __init__(self):
        raise TypeError("Tato třída je statická a nemůže být instancována.")

