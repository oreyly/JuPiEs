from __future__ import annotations
import random
import tkinter as tk
from typing import TYPE_CHECKING, Callable, Dict, Tuple, Optional, Any
from Errors import ERROR_CODES
from GAME_BOOL import PLAYER_COLOR
from GameResult import GAME_RESULT
from GameState import GAME_STATE
from Logger import Logger
from OPCODE import OPCODE
from Packet import Packet
from PieceType import PIECE_TYPE
from Request import IncomingRequest
from RequestManager import RequestManager
from checkers import CheckersBoard

if TYPE_CHECKING:
    from Program import Program
    from GameLobby import GameLobby

class GameRoom:
    # Seznam členských proměnných (Property definitions)
    _program: Program
    _nextProcessFunction: Optional[Callable[[IncomingRequest], None]]
    myColor: PLAYER_COLOR
    gameLobby: GameLobby
    movingColor: PLAYER_COLOR
    window: tk.Toplevel
    game: CheckersBoard
    cellSize: int
    activePlayers: Dict[PLAYER_COLOR, bool]
    selectedPos: Optional[Tuple[int, int]]
    uiElements: Dict[PLAYER_COLOR, Dict[str, Any]]
    whiteName: Optional[str]
    blackName: Optional[str]
    topPanel: tk.Frame
    canvas: tk.Canvas
    bottomPanel: tk.Frame
    CanClick: bool
    
    _opponentArrivedPacket: Packet | None
    _opponentGameFinished: Packet | None
    _gameResult: GAME_RESULT | None

    def __init__(self, program: Program, gameLobby: GameLobby, myColor: PLAYER_COLOR, 
                 whiteName: Optional[str] = None,
                 blackName: Optional[str] = None):
        
        self._program = program
        self.gameLobby = gameLobby
        self.gameLobby.RegisterProcessingFunction(self.processIncomingMessage)
        
        self.CanClick = True
        
        self._gameResult = None
        self.myColor = myColor
        self.nextProcessFunction = None
        
        self.window = tk.Toplevel(self._program.Root)
        self.window.title("Dáma - Python")
        self.window.protocol("WM_DELETE_WINDOW", self.onExitClick)

        self.game = CheckersBoard(self._program,self)
        self.cellSize = 80
        self.activePlayers = {PLAYER_COLOR.WHITE: False, PLAYER_COLOR.BLACK: False}
        self.selectedPos = None
        self.uiElements = {}
        self.whiteName = whiteName
        self.blackName = blackName

        # Horní panel
        self.topPanel = tk.Frame(self.window)
        self.topPanel.pack(fill="x", pady=5)
        opponentColor = PLAYER_COLOR.BLACK if self.myColor == PLAYER_COLOR.WHITE else PLAYER_COLOR.WHITE
        self.createPlayerSlot(self.topPanel, opponentColor)

        # Canvas
        self.canvas = tk.Canvas(
            self.window, 
            width=self.game.SIZE * self.cellSize, 
            height=self.game.SIZE * self.cellSize
        )
        self.canvas.pack()
        
        # Spodní panel
        self.bottomPanel = tk.Frame(self.window)
        self.bottomPanel.pack(fill="x", pady=5)
        self.createPlayerSlot(self.bottomPanel, self.myColor)

        self.canvas.bind("<Button-1>", self.onClick)
        self.drawBoard()

    def ShowResult(self):
        if(not self._gameResult):
            Logger.LogError(GameRoom, ERROR_CODES.OBJECT_NOT_INITIALIZED, [GAME_RESULT.__name__])
            return
        
        popup = tk.Toplevel()
        popup.title("Dáma hlásí...")
        popup.geometry("350x200")
        popup.resizable(False, False)
        
        hlasky = {
            GAME_RESULT.WIN: [
                "Tvoje dáma právě provedla vítězný tanec!",
                "Soupeřovy figurky šly dobrovolně do krabice.",
                "Gratuluji, tvoje IQ právě stouplo o 2 políčka!"
            ],
            GAME_RESULT.LOSS: [
                "Tvoje figurky byly vyslány na dovolenou... mimo šachovnici.",
                "Tohle nebyla prohra, to byl strategický ústup do krabice.",
                "I dřevěná figurka má někdy špatný den."
            ],
            GAME_RESULT.DRAW: [
                "Nikdo nevyhrál, figurky se dohodly na příměří.",
                "Patová situace. Figurky odmítají dál skákat.",
                "Smírná dohoda. Jděte radši na kafe."
            ]
        }

        selectedHlaska = random.choice(hlasky.get(self._gameResult, ["Něco se stalo..."]))
        
        barvy = {
            GAME_RESULT.WIN: "#4CAF50",
            GAME_RESULT.LOSS: "#F44336",
            GAME_RESULT.DRAW: "#FF9800"
        }
        color = barvy.get(self._gameResult, "gray")

        popup.configure(bg=color)

        tk.Label(popup, text=str(self._gameResult).upper(), font=("Comic Sans MS", 20, "bold"), 
                bg=color, fg="white").pack(pady=10)
        
        label_msg = tk.Label(popup, text=selectedHlaska, font=("Arial", 11, "italic"), 
                            bg=color, fg="white", wraplength=300)
        label_msg.pack(pady=10)

        def shake(count: int=0):
            if count < 10:
                x = popup.winfo_x()
                y = popup.winfo_y()
                shift = 5 if count % 2 == 0 else -5
                popup.geometry(f"+{x+shift}+{y}")
                popup.after(50, lambda: shake(count + 1))

        tk.Button(popup, text="Beru na vědomí", command=lambda : [popup.destroy(), self.EndRoom()],
                relief="flat", bg="white").pack(pady=10)
        
        popup.after(100, shake)
    
    def EndRoom(self):
        self.window.destroy()
        self.gameLobby.unRegisterProcessingFunction()
        self._program.Root.deiconify()
        self._program.Root.update_idletasks()
        """while (not self.gameLobby.RefButton):
            Logger.LogError(GameRoom, ERROR_CODES.OBJECT_NOT_INITIALIZED, [tk.Button.__name__])
            time.sleep(0.1)
        
        self.gameLobby.RefButton.invoke()"""
    
    def registerProcessingFunction(self, nextProcessFunction: Callable[[IncomingRequest], None]):
        self._nextProcessFunction = nextProcessFunction
    
    def processIncomingMessage(self, incomingRequest: IncomingRequest):
        if(not self._program.ReqManager):
            Logger.LogError(GameRoom, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager])
            return
        
        match(incomingRequest.DemandMessage.MainPacket.Opcode):
            case OPCODE.OPPONENT_ARRIVED:
                self._opponentArrivedPacket = incomingRequest.DemandMessage.MainPacket
                self._program.ReqManager.SendResponse(OPCODE.KNOW_ABOUT_HIM, [], self.onTimeoutOppnonentArrived)
                targetColor = PLAYER_COLOR.WHITE if not self.whiteName else PLAYER_COLOR.BLACK
                self.addPlayer(targetColor, incomingRequest.DemandMessage.MainPacket.Parameters[0], isReady=False)
            case OPCODE.GAME_FINISHED:
                self._opponentGameFinished = incomingRequest.DemandMessage.MainPacket
                self._program.ReqManager.SendResponse(OPCODE.FINALY_END, [], self.onTimeoutGameFinished)
                obtainedResult = GAME_STATE(int(incomingRequest.DemandMessage.MainPacket.Parameters[0]))
                
                self._gameResult = (
                    GAME_RESULT.DRAW if obtainedResult == GAME_STATE.DRAW else
                    GAME_RESULT.WIN if obtainedResult == GAME_STATE.WHITE_WIN and self.myColor == PLAYER_COLOR.WHITE  else
                    GAME_RESULT.WIN if obtainedResult == GAME_STATE.BLACK_WIN and self.myColor == PLAYER_COLOR.BLACK  else
                    GAME_RESULT.LOSS
                )
                
                self.ShowResult()
                self.CanClick = False
            case _:
                if(self._nextProcessFunction):
                    self._nextProcessFunction(incomingRequest)
                else:
                    raise Exception("Neznámý OPCODE")
    
    def onTimeoutOppnonentArrived(self):
        if(not self._opponentArrivedPacket):
            Logger.LogError(GameRoom, ERROR_CODES.RESPONSE_TO_UNKNOWN_REQUEST)
            return
        Logger.LogError(GameRoom, ERROR_CODES.SERVER_NOT_KNOW_RESPONSE, [self._opponentArrivedPacket.CreateString()])
        
    def onTimeoutGameFinished(self):
        if(not self._opponentGameFinished):
            Logger.LogError(GameRoom, ERROR_CODES.RESPONSE_TO_UNKNOWN_REQUEST)
            return
        Logger.LogError(GameRoom, ERROR_CODES.SERVER_NOT_KNOW_RESPONSE, [self._opponentGameFinished.CreateString()])
        
    def Open(self) -> None:
        if (self.whiteName):
            self.addPlayer(PLAYER_COLOR.WHITE, self.whiteName)
        if (self.blackName):
            self.addPlayer(PLAYER_COLOR.BLACK, self.blackName)

    def removePlayer(self, player: PLAYER_COLOR) -> None:
        self.activePlayers[player] = False
        
        ui = self.uiElements[player]
        ui["nameLabel"].config(
            text="Čekání na hráče...", 
            font=("Arial", 12, "italic"), 
            fg="gray"
        )
        
        self.selectedPos = None
        self.drawBoard()

    def createPlayerSlot(self, parent: tk.Frame, player: PLAYER_COLOR) -> None:
        nameLabel = tk.Label(parent, text="Čekání na hráče...", font=("Arial", 12, "italic"), fg="gray")
        nameLabel.pack(side="left", padx=10)

        if(player == self.myColor):
            exitBtn = tk.Button(parent, text="Odejít", command=self.onExitClick, fg="red")
            self.uiElements[player] = {
                "nameLabel": nameLabel,
                "exitBtn": exitBtn
            }
            exitBtn.pack(side="left", padx=10)
        else:
            self.uiElements[player] = {
                "nameLabel": nameLabel,
            }

    def addPlayer(self, player: PLAYER_COLOR, name: str, isReady: bool = False) -> None:
        if(not name):
            self.removePlayer(player)
            return
        
        self.activePlayers[player] = True
        
        ui = self.uiElements[player]
        ui["nameLabel"].config(text=name, font=("Arial", 12, "bold"), fg="black")

    def drawBoard(self) -> None:
        self.canvas.delete("all")
        for r in range(self.game.SIZE):
            for c in range(self.game.SIZE):
                # Transformace indexů pro zobrazení
                # Pokud jsem černý, r=0 (top) se vykreslí jako r=7 (bottom)
                vis_r = (self.game.SIZE - 1 - r) if self.myColor == PLAYER_COLOR.BLACK else r
                vis_c = (self.game.SIZE - 1 - c) if self.myColor == PLAYER_COLOR.BLACK else c

                x1, y1 = vis_c * self.cellSize, vis_r * self.cellSize
                x2, y2 = x1 + self.cellSize, y1 + self.cellSize
                
                color = "#DDBB99" if (r + c) % 2 == 0 else "#663300"
                
                # Zvýraznění výběru (používáme logické r, c)
                if self.selectedPos == (r, c):
                    color = "#AAFF22"
                
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
                
                piece = self.game.board[r][c]
                if piece:
                    # Předáme transformované vizuální souřadnice do drawPiece
                    self.drawPieceAtVisual(vis_r, vis_c, piece)

    def drawPieceAtVisual(self, vis_r: int, vis_c: int, piece: Any) -> None:
        padding = 10
        x1, y1 = vis_c * self.cellSize + padding, vis_r * self.cellSize + padding
        x2, y2 = (vis_c + 1) * self.cellSize - padding, (vis_r + 1) * self.cellSize - padding
        
        fillColor = "white" if piece.owner == PLAYER_COLOR.WHITE else "#222222"
        outlineColor = "black" if piece.owner == PLAYER_COLOR.WHITE else "white"
        
        self.canvas.create_oval(x1, y1, x2, y2, fill=fillColor, outline=outlineColor, width=2)
        if piece.type == PIECE_TYPE.KING:
            self.canvas.create_text(
                (x1 + x2) / 2, (y1 + y2) / 2, 
                text="K", fill="gold", font=("Arial", 24, "bold")
            )

    def onClick(self, event: tk.Event) -> None:
        activeList = [p for p, active in self.activePlayers.items() if active]
        
        if len(activeList) < 2 or self.game.currentPlayer != self.myColor or not self.CanClick:
            return
        
        # Výpočet vizuálních souřadnic
        vis_col = event.x // self.cellSize
        vis_row = event.y // self.cellSize
        
        # Transformace zpět na logické souřadnice
        if self.myColor == PLAYER_COLOR.BLACK:
            row = (self.game.SIZE - 1) - vis_row
            col = (self.game.SIZE - 1) - vis_col
        else:
            row = vis_row
            col = vis_col
            
        clickedPos = (row, col)

        # ... zbytek logiky onClick zůstává stejný ...
        if self.selectedPos is None:
            piece = self.game.board[row][col]
            if piece and piece.owner == self.game.currentPlayer:
                self.selectedPos = clickedPos
        else:
            if(self.game.isAnyValidMove(self.selectedPos, clickedPos)):
                self.game.TryMove(self.selectedPos, clickedPos)
                self.selectedPos = None
            else:
                piece = self.game.board[row][col]
                if piece and piece.owner == self.game.currentPlayer:
                    self.selectedPos = clickedPos
                else:
                    self.selectedPos = None
                    

        self.drawBoard()
        
        """
        if self.game.isGameOver():
            winner = "Černý" if self.game.currentPlayer == PLAYER_COLOR.WHITE else "Bílý"
            messagebox.showinfo("Konec hry", f"Hra skončila! Vítěz: {winner}")
            self.game = CheckersBoard()
            for p in self.readyStates:
                self.readyStates[p] = False
            self.updateReadyVisuals()
            self.drawBoard()
        """
    
    def onTimeoutQuit(self):
        Logger.LogError(GameRoom, ERROR_CODES.SERVER_NOT_KNOW_QUIT)
    
    def QuitRoom(self, responseParams: list[str]):
        self.EndRoom()
    
    def onExitClick(self):
        if(self._gameResult):
            self.EndRoom()
            return
        
        if(not self._program.ReqManager):
            Logger.LogError(GameRoom, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        
        self._program.ReqManager.CreateDemand(OPCODE.GAME_QUIT, [], self.onTimeoutQuit, self.QuitRoom, OPCODE.GAME_QUITED)
        self.EndRoom()
