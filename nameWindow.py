from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

from Errors import ERROR_CODES
from GAME_BOOL import GAME_BOOL
from Logger import Logger
from OPCODE import OPCODE
from RequestManager import RequestManager
from Server import Server
from Utils import Utils

if TYPE_CHECKING:
    from Program import Program
    
class NameDialog:
    _program: Program
    NameRegistered: bool
    
    def __init__(self, program: Program):
        self._program = program
        self.NameRegistered = False

    def SetupGui(self) -> None:
        # Nastavení hlavního okna
        self._program.Root.title("Zadání jména")
        self._program.Root.geometry("300x200")

        self._program.Root.protocol("WM_DELETE_WINDOW", self._program.Leave)
        # Registrace validační funkce
        self.vcmd = (self._program.Root.register(self.ValidateInput), '%P')

        # Hlavní kontejner
        self._mainFrame = tk.Frame(self._program.Root)
        self._mainFrame.pack(pady=20, padx=20, fill="both", expand=True)

        # Label
        self.label = tk.Label(self._mainFrame, text="Zadejte jméno (max 10 alfanum. znaků):")
        self.label.pack(pady=10)

        # Entry s validací
        self.entry = tk.Entry(self._mainFrame, validate="key", validatecommand=self.vcmd)
        self.entry.pack(pady=5)
        self.entry.focus_set()

        # Tlačítko Odeslat
        self.submit_btn = tk.Button(self._mainFrame, text="Odeslat", command=self.SubmitName)
        self.submit_btn.pack(pady=10)

    def ValidateInput(self, newValue: str):
        """Validuje, zda je vstup prázdný nebo alfanumerický do 10 znaků."""
        if newValue == "":
            return True
        if len(newValue) <= 10 and newValue.isalnum():
            return True
        return False

    def SubmitName(self):
        if(not self._program.ReqManager):
            Logger.LogError(NameDialog, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        
        name = self.entry.get()
        if name:
            self.entry.config(state="readonly")
            self.submit_btn.config(state="disabled")
            self._program.ReqManager.CreateDemand(OPCODE.WANA_NAME, [name], self.ConFailed, self.ConSucceded, OPCODE.VALID_NAME)
        else:
            messagebox.showwarning("Chyba", "Pole nesmí být prázdné.")
            
    def ConFailed(self):
        Logger.LogError(NameDialog, ERROR_CODES.SERVER_NOT_KNOW_NAME)
    
    @Utils.UpdateLastEcho
    def ConSucceded(self, responseParams: list[str]):
        if(GAME_BOOL(int(responseParams[0])) == GAME_BOOL.FALSE):
            messagebox.showwarning("Chyba", "Jméno je již obsazené.")
            self.entry.config(state="normal")
            self.submit_btn.config(state="normal")
            return
        
        Server.MyName = self.entry.get()
        self.NameRegistered = True
        Logger.LogMessage(NameDialog, f"Klient úspěšně zaregistroval své jméno: {Server.MyName}")
        for widget in self._program.Root.winfo_children():
            widget.destroy()
            
        self._program.OpenLobby()

    def Open(self):
        self.SetupGui()
