from __future__ import annotations
import base64
import random
import tkinter as tk
from typing import TYPE_CHECKING, Callable, Dict, Tuple, Optional, Any
from Errors import ERROR_CODES
from GAME_BOOL import GAME_BOOL, PLAYER_COLOR
from GameResult import GAME_RESULT
from GameState import GAME_STATE
from Logger import Logger
from OPCODE import OPCODE
from Packet import Packet
from PieceType import PIECE_TYPE
from Request import IncomingRequest
from RequestManager import RequestManager
from Utils import Utils
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
    _opponentMissingPacket: Packet | None
    _gameResult: GAME_RESULT | None

    def __init__(self, program: Program, gameLobby: GameLobby, myColor: PLAYER_COLOR, 
                whiteName: Optional[str] = None,
                blackName: Optional[str] = None,
                reconected: bool = False
                ):
        
        
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
        
        if(not self._program.ReqManager):
            Logger.LogError(GameRoom, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        
        if(not self.blackName or not self.whiteName):
            return
        
        self._program.ReqManager.CreateDemand(OPCODE.IS_HE_ALIVE, [], self.onTimeoutHesMissing, self.onAliveObtained, OPCODE.HE_IS_ALIVE)
        
        if(reconected):
            self._program.ReqManager.CreateDemand(OPCODE.GET_POSITION, [], self.onTimeoutGetPosition, self.CreatePosition, OPCODE.HERE_POSITION)

    def onTimeoutGetPosition(self):
        Logger.LogError(GameRoom, ERROR_CODES.I_DONT_KNOW_POSITION)
    
    Utils.UpdateLastEcho
    def CreatePosition(self, responseParams: list[str]):
        self.game.currentPlayer = PLAYER_COLOR(int(responseParams[1]))
        
        raw_bytes = base64.b64decode(responseParams[0])
        
        bit_string = "".join(bin(byte)[2:].zfill(8) for byte in raw_bytes)

        bit_ptr = 0
        
        self.game.board = [[None for _ in range(self.game.SIZE)] for _ in range(self.game.SIZE)]

        for r in range(self.game.SIZE):
            for c in range(self.game.SIZE):
                if (r + c) % 2 != 0:
                    bits = bit_string[bit_ptr:bit_ptr + 3]
                    bit_ptr += 3

                    if bits == "000":
                        self.game.board[r][c] = None
                    else:
                        owner = PLAYER_COLOR.WHITE if bits[0] == '1' else PLAYER_COLOR.BLACK
                        p_type = PIECE_TYPE.KING if bits[1] == '1' else PIECE_TYPE.MAN
                        
                        from checkers import Piece
                        self.game.board[r][c] = Piece(owner, p_type)

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
        self._program.UnregisterOnReconnect()
        self.gameLobby.unRegisterProcessingFunction()
        self._program.Root.deiconify()
        self._program.Root.update_idletasks()
        self._program.Root.after_idle(self.gameLobby.RegisterOnReconnect)
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
                otherName = self.whiteName if self.myColor == PLAYER_COLOR.BLACK else self.blackName
                if(otherName == incomingRequest.DemandMessage.MainPacket.Parameters[0]):
                    return
                
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
            case OPCODE.HES_MISSING:
                self._opponentMissingPacket = incomingRequest.DemandMessage.MainPacket
                self._program.ReqManager.SendResponse(OPCODE.THATS_A_SHAME, [], self.onTimeoutHesMissing)
                self.updatePlayerStatus(PLAYER_COLOR.WHITE if self.myColor == PLAYER_COLOR.BLACK else PLAYER_COLOR.BLACK, GAME_BOOL(int(incomingRequest.DemandMessage.MainPacket.Parameters[0])) != GAME_BOOL.TRUE)
            case _:
                if(self._nextProcessFunction):
                    self._nextProcessFunction(incomingRequest)
                else:
                    raise Exception("Neznámý OPCODE")
    
    def onTimeoutHesMissing(self):
        if(not self._opponentMissingPacket):
            Logger.LogError(GameRoom, ERROR_CODES.RESPONSE_TO_UNKNOWN_REQUEST)
            return
        
        Logger.LogError(GameRoom, ERROR_CODES.SERVER_NOT_KNOW_RESPONSE, [self._opponentMissingPacket.CreateString()])
    
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
        
    def OnReconnect(self):
        if(not self._program.ReqManager):
            Logger.LogError(CheckersBoard, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        
        self._program.ReqManager.CreateDemand(OPCODE.WHAT_HAPPEND, [], self.onTimeoutWhatHappend, self.onLastMoveObtained, OPCODE.THIS_HAPPEND)
        self._program.ReqManager.CreateDemand(OPCODE.IS_HE_ALIVE, [], self.onTimeoutHesMissing, self.onAliveObtained, OPCODE.HE_IS_ALIVE)
    
    def onTimeoutHeAlive(self):
        Logger.LogError(GameRoom, ERROR_CODES.I_DONT_KNOW_POSITION)
    
    def onTimeoutWhatHappend(self):
        Logger.LogError(GameRoom, ERROR_CODES.I_DONT_KNOW_HE_ALIVE)
    
    def onAliveObtained(self, responseParams: list[str]):
        self.updatePlayerStatus(PLAYER_COLOR.WHITE if self.myColor == PLAYER_COLOR.BLACK else PLAYER_COLOR.BLACK, GAME_BOOL(int(responseParams[0])) == GAME_BOOL.TRUE)
        
    @Utils.UpdateLastEcho
    def onLastMoveObtained(self, responseParams: list[str]):
        self.CanClick = True
        if(all([int(r) == 0 for r in responseParams])):
            return
        
        was = self.game.isAnyValidMove((int(responseParams[0]), int(responseParams[1])), (int(responseParams[2]), int(responseParams[3])))
        
        if(was):
            self.game.movePiece((int(responseParams[0]), int(responseParams[1])), (int(responseParams[2]), int(responseParams[3])))
            self.drawBoard()

    def Open(self) -> None:
        self._program.RegisterOnReconnect(self.OnReconnect)
        
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
        self.updatePlayerStatus(player, False)
        self.selectedPos = None
        self.drawBoard()

    def createPlayerSlot(self, parent: tk.Frame, player: PLAYER_COLOR) -> None:

        infoFrame = tk.Frame(parent)
        infoFrame.pack(side="left", padx=10)

        statusCanvas = tk.Canvas(infoFrame, width=12, height=12, highlightthickness=0)
        statusCanvas.pack(side="left", padx=(0, 5))
        
        statusCanvas.create_oval(2, 2, 10, 10, fill="gray", tags="dot")
        
        nameLabel = tk.Label(parent, text="Čekání na hráče...", font=("Arial", 12, "italic"), fg="gray")
        nameLabel.pack(side="left")
        
        if(player == self.myColor):
            exitBtn = tk.Button(parent, text="Odejít", command=self.onExitClick, fg="red")
            exitBtn.pack(side="left", padx=10)
            self.uiElements[player] = {
                "nameLabel": nameLabel,
                "statusCanvas": statusCanvas,
                "exitBtn": exitBtn
            }
        else:
            self.uiElements[player] = {
                "nameLabel": nameLabel,
                "statusCanvas": statusCanvas,
            }

    def updatePlayerStatus(self, player: PLAYER_COLOR, online: bool) -> None:
        if player in self.uiElements:
            color = "#4CAF50" if online else "#F44336" 
            canvas = self.uiElements[player]["statusCanvas"]
            canvas.itemconfig("dot", fill=color)

    def highlightCurrentTurn(self) -> None:
        for color, ui in self.uiElements.items():
            if(not ui["nameLabel"]):
                continue
            is_moving = (color == self.game.currentPlayer)
            if is_moving:
                new_font = ("Arial", 12, "bold", "underline")
            else:
                    new_font = ("Arial", 12, "bold")
                
            ui["nameLabel"].config(font=new_font)

    def addPlayer(self, player: PLAYER_COLOR, name: str, isReady: bool = False) -> None:
        if(not name):
            self.removePlayer(player)
            self.highlightCurrentTurn()
            return
        
        self.activePlayers[player] = True
        
        ui = self.uiElements[player]
        ui["nameLabel"].config(text=name, font=("Arial", 12, "bold"), fg="black")
        self.updatePlayerStatus(player, True)
        self.highlightCurrentTurn()

    def drawBoard(self) -> None:
        self.highlightCurrentTurn()
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
    
    @Utils.UpdateLastEcho
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
