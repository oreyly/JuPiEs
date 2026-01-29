from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable, Optional, Tuple
from Errors import ERROR_CODES
from GameRoom import GameRoom
from Logger import Logger
from OPCODE import OPCODE
from Request import IncomingRequest
from RequestManager import RequestManager
from Server import Server
from SideSelectionDialog import SideSelectionDialog
from GAME_BOOL import GAME_BOOL, PLAYER_COLOR
from Utils import Utils

if TYPE_CHECKING:
    from Program import Program

class GameLobby:
    _nextProcessFunction: Callable[[IncomingRequest], None] | None
    
    # Definice členských proměnných mimo konstruktor
    _topFrame: Optional[tk.Frame]
    _headerFrame: Optional[tk.Frame]
    _container: Optional[tk.Frame]
    _canvas: Optional[tk.Canvas]
    _scrollbar: Optional[ttk.Scrollbar]
    _scrollableFrame: Optional[tk.Frame]
    _gameRoom: Optional[GameRoom]
    _selectedColor: Optional[PLAYER_COLOR]
    
    RefButton: Optional[tk.Button]
    
    _program: Program

    def __init__(self, program: Program):
        self._program = program
        self._program.RegisterProcessingFunction(self.ProcessIncommingMessage)
        
        self._topFrame = None
        self._headerFrame = None
        self._container = None
        self._canvas = None
        self._scrollbar = None
        self._scrollableFrame = None

    def RegisterProcessingFunction(self, nextProcessFunction: Callable[[IncomingRequest], None]):
        self._nextProcessFunction = nextProcessFunction
        
    def unRegisterProcessingFunction(self):
        self._nextProcessFunction = None
        
    def ProcessIncommingMessage(self, incomingRequest: IncomingRequest):
        match(incomingRequest.DemandMessage.MainPacket.Opcode):
            case _:
                if(self._nextProcessFunction):
                    self._nextProcessFunction(incomingRequest)
                else:
                    raise Exception("Nelze zpracovat")

    def SetupGui(self) -> None:
        self._program.Root.title("Game Lobby Manager")
        self._program.Root.geometry("500x400")

        self._topFrame = tk.Frame(self._program.Root)
        self._topFrame.pack(pady=10, fill="x")

        self._program.Root.protocol("WM_DELETE_WINDOW", self._program.Leave)
        tk.Button(self._topFrame, text="Vytvořit lobby", command=self.OpenSideSelectionWindow).pack(side="left", padx=5)
        self. RefButton = tk.Button(self._topFrame, text="Obnovit", command=self.RefreshRooms).pack(side="left", padx=5)
        tk.Button(self._topFrame, text="Odpojit", command=self._program.Leave).pack(side="left", padx=5)

        self._headerFrame = tk.Frame(self._program.Root)
        self._headerFrame.pack(fill="x", padx=10)
        tk.Label(self._headerFrame, text="ID", width=10, anchor="w", font=('Arial', 10, 'bold')).pack(side="left")
        tk.Label(self._headerFrame, text="Bílý hráč", width=15, font=('Arial', 10, 'bold')).pack(side="left")
        tk.Label(self._headerFrame, text="Černý hráč", width=15, font=('Arial', 10, 'bold')).pack(side="left")

        self._container = tk.Frame(self._program.Root)
        self._container.pack(fill="both", expand=True, padx=10, pady=5)
        self._canvas = tk.Canvas(self._container)
        self._scrollbar = ttk.Scrollbar(self._container, orient="vertical", command=self._canvas.yview) # type: ignore
        self._scrollableFrame = tk.Frame(self._canvas)

        self._scrollableFrame.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))) # type: ignore
        self._canvas.create_window((0, 0), window=self._scrollableFrame, anchor="nw")
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")

        self._canvas.bind_all("<MouseWheel>", self.OnMouseWheel)
        self._canvas.bind_all("<Button-4>", self.OnMouseWheel)
        self._canvas.bind_all("<Button-5>", self.OnMouseWheel)

        self.RefreshRooms()
        
    def OnMouseWheel(self, Event: tk.Event) -> None:
        """Zajišťuje posun Canvasu při točení kolečkem."""
        if not self._canvas:
            return
            
        if Event.num == 4: # Linux scroll up
            self._canvas.yview_scroll(-1, "units")
        elif Event.num == 5: # Linux scroll down
            self._canvas.yview_scroll(1, "units")
        else: # Windows a macOS
            self._canvas.yview_scroll(int(-1 * (Event.delta / 120)), "units")

    def AddLobbyRow(self, roomId: int, WhiteBool: GAME_BOOL, BlackBool: GAME_BOOL) -> None:
        Row = tk.Frame(self._scrollableFrame)
        Row.pack(fill="x", pady=2)

        tk.Label(Row, text=str(roomId), width=12, anchor="w").pack(side="left")

        # Bílý hráč
        if WhiteBool == GAME_BOOL.TRUE:
            tk.Label(Row, text="Obsazeno", fg="red", width=15).pack(side="left", padx=5)
        else:
            tk.Button(Row, text="Připojit (Bílý)", width=15, 
                      command=lambda: self.JoinRoomAs(roomId, PLAYER_COLOR.WHITE)).pack(side="left", padx=5)

        # Černý hráč
        if BlackBool == GAME_BOOL.TRUE:
            tk.Label(Row, text="Obsazeno", fg="red", width=15).pack(side="left", padx=5)
        else:
            tk.Button(Row, text="Připojit (Černý)", width=15, 
                      command=lambda: self.JoinRoomAs(roomId, PLAYER_COLOR.BLACK)).pack(side="left", padx=5)

    def RefreshRooms(self) -> None:
        Logger.LogMessage(GameLobby,"REFFF")
        if(not self._program.ReqManager):
            Logger.LogError(GameLobby, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        
        self._program.ReqManager.CreateDemand(OPCODE.WANA_ROOMS, [], self.ConFailed, self.ConSucceded, OPCODE.ROOM_LIST)
    
    def ConFailed(self):
        Logger.LogError(GameLobby, ERROR_CODES.ROOM_LOAD_FAIL)
        
    @Utils.UpdateLastEcho
    def ConSucceded(self, responseParams: list[str]):
        rooms: list[Tuple[int, GAME_BOOL, GAME_BOOL]] = []
        for i in range(0, len(responseParams), 3):
            rooms.append((
                int(responseParams[i]),
                GAME_BOOL(int(responseParams[i+1])),
                GAME_BOOL(int(responseParams[i+2]))
            ))
        
        rooms.sort(key=lambda r: r[0])
        
        self.ListRooms(rooms)
    
    def ListRooms(self, rooms: list[Tuple[int, GAME_BOOL, GAME_BOOL]]):
        if self._scrollableFrame:
            for Widget in self._scrollableFrame.winfo_children():
                Widget.destroy()
        for Lobby in rooms:
            self.AddLobbyRow(Lobby[0], Lobby[1], Lobby[2])

    def OpenSideSelectionWindow(self) -> None:
        Dialog = SideSelectionDialog(self._program.Root, self.CreateRoomAs)
        Dialog.Show()

    def CreateRoomAs(self, color: PLAYER_COLOR) -> None:
        if(not self._program.ReqManager):
            Logger.LogError(GameLobby, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        self._selectedColor = color
        self._program.ReqManager.CreateDemand(OPCODE.CREATE_ROOM, [str(color)], self.ConFailed, self.RoomCreateResponse,OPCODE.ROOM_CREATED)

    @Utils.UpdateLastEcho
    def RoomCreateResponse(self, responseParams: list[str]):
        if(self._selectedColor is None):
            Logger.LogError(GameLobby, ERROR_CODES.OBJECT_NOT_INITIALIZED, [PLAYER_COLOR.__name__])
            return
        
        if(GAME_BOOL(int(responseParams[0])) == GAME_BOOL.FALSE):
            Logger.LogMessage(GameLobby, "Server dosáhl maximálního počtu roomek a nedovolil vytvořit další.")
            messagebox.showwarning("Chyba", "Server dosáhl maximálního počtu roomek a nedovolil vytvořit další.")
            self.RefreshRooms()
            return
        
        if self._scrollableFrame:
            for Widget in self._scrollableFrame.winfo_children():
                Widget.destroy()
                
        iAmWhite = self._selectedColor == PLAYER_COLOR.WHITE
        
        self._program.UnregisterOnReconnect()
        self._program.Root.withdraw()
        self._gameRoom = GameRoom(self._program, self, self._selectedColor,
                                whiteName=Server.MyName if iAmWhite else None,
                                blackName=None if iAmWhite else Server.MyName)
        self._gameRoom.Open()

    def JoinRoomAs(self, roomId: int, color: PLAYER_COLOR) -> None:
        if(not self._program.ReqManager):
            Logger.LogError(GameLobby, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        self._selectedColor = color
        self._program.ReqManager.CreateDemand(OPCODE.GET_TO_ROOM, [str(roomId), str(color)],self.ConFailed,self.JoinedRoom,OPCODE.GOT_TO_ROOM)

    @Utils.UpdateLastEcho
    def JoinedRoom(self, responseParams: list[str]):
        if(self._selectedColor is None):
            Logger.LogError(GameLobby, ERROR_CODES.OBJECT_NOT_INITIALIZED, [PLAYER_COLOR.__name__])
            return
        
        if(GAME_BOOL(int(responseParams[0])) == GAME_BOOL.FALSE):
            messagebox.showwarning("Chyba", "Pozice v roomce je nedostupná.")
            self.RefreshRooms()
            return
        
        iAmWhite = self._selectedColor == PLAYER_COLOR.WHITE
        
        if self._scrollableFrame:
            for Widget in self._scrollableFrame.winfo_children():
                Widget.destroy()
            
        self._program.UnregisterOnReconnect()
        self._program.Root.withdraw()
        self._gameRoom = GameRoom(self._program, self, self._selectedColor,
                                whiteName=Server.MyName if iAmWhite else responseParams[1],
                                blackName=responseParams[1] if iAmWhite else Server.MyName
                                )
        self._gameRoom.Open()
    
    def RegisterOnReconnect(self):
        self._program.RegisterOnReconnect(self.OnReconnect)
    
    def OnReconnect(self):
        self.RefreshRooms()
    
    def Open(self) -> None:
            self.SetupGui()

