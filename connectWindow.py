from __future__ import annotations
import threading
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING
from Errors import ERROR_CODES
from Logger import Logger
from OPCODE import OPCODE
from Server import Server, Address
from RequestManager import RequestManager

if TYPE_CHECKING:
    from Program import Program
    
class ConnectionDialog:
    _program: Program
    Connected: bool
    
    def __init__(self, program : Program):
        self.Connected = False
        self._program = program

    def SetupGui(self) -> None:
        # Konfigurace existujícího rootu
        self._program.Root.title("Nastavení připojení")
        self._program.Root.geometry("300x250")

        # Hlavní kontejner pro vycentrování prvků
        self._container = tk.Frame(self._program.Root)
        self._container.pack(expand=True, fill="both", padx=20, pady=10)

        # IP Adresa sekce
        tk.Label(self._container, text="IP Adresa:", font=('Arial', 10, 'bold')).pack(pady=(5, 0))
        self.entry_ip = tk.Entry(self._container, justify="center")
        self.entry_ip.insert(0, "10.0.1.72")
        self.entry_ip.pack(pady=5, fill="x")

        # Port sekce
        tk.Label(self._container, text="Port:", font=('Arial', 10, 'bold')).pack(pady=(10, 0))
        self.entry_port = tk.Entry(self._container, justify="center")
        self.entry_port.insert(0, "7890")
        self.entry_port.pack(pady=5, fill="x")

        # Tlačítko pro potvrzení
        self.submit_btn = tk.Button(
            self._container, 
            text="Potvrdit a odeslat", 
            command=self.submit,
            bg="#e1e1e1"
        )
        self.submit_btn.pack(pady=20, ipadx=10)

    def ConFailed(self):
        Logger.LogError(ConnectionDialog, ERROR_CODES.CONNECTION_FAILED, [Server.ServerAddress])
    
    def ConSucceded(self, responseParams: list[str]):
        if(int(responseParams[0]) == 0):
            messagebox.showwarning("Chyba", "K serveru je připojeno maximální množství klientů.")
            Logger.LogMessage(ConnectionDialog, "K serveru je připojeno maximální množství klientů")
            return
        
        self.Connected = True
        Server.MyId = int(responseParams[0])
        Logger.LogMessage(ConnectionDialog,"Klient se úspěšně připojil k serveru.")
        #self._program.Running = True
        #self._program.CheckerThread = threading.Thread(target=self._program.ServerChecker ,daemon=True)
        #self._program.CheckerThread.start()
        
        for widget in self._program.Root.winfo_children():
            widget.destroy()
        
        self._program.RegisterName()
        
    def submit(self):
        if(not self._program.ReqManager):
            Logger.LogError(ConnectionDialog, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        
        Server.ServerAddress = Address(self.entry_ip.get(), int(self.entry_port.get()))
        
        self._program.ReqManager.CreateDemand(
            opcode=OPCODE.CON,
            params=[],
            onFailure=self.ConFailed,
            onSuccess=self.ConSucceded,
            expectedOpcode=OPCODE.CON_AS
        )

    def Open(self):
        self.SetupGui()
        self._program.Root.mainloop()
