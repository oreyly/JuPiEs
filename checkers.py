from __future__ import annotations

from tkinter import messagebox
from typing import TYPE_CHECKING, Callable, Optional, List, Tuple
from Errors import ERROR_CODES
from GAME_BOOL import GAME_BOOL, PLAYER_COLOR
from Logger import Logger
from OPCODE import OPCODE
from Packet import Packet
from PieceType import PIECE_TYPE
from Request import IncomingRequest
from RequestManager import RequestManager

if TYPE_CHECKING:
    from Program import Program
    from GameRoom import GameRoom

class Piece:
    # Členské proměnné
    owner: PLAYER_COLOR
    type: PIECE_TYPE

    def __init__(self, owner: PLAYER_COLOR, PIECE_TYPE: PIECE_TYPE):
        self.owner = owner
        self.type = PIECE_TYPE

class CheckersBoard:
    # Seznam členských proměnných
    SIZE: int = 8
    board: List[List[Optional[Piece]]]
    currentPlayer: PLAYER_COLOR
    multiJumpPos: Optional[Tuple[int, int]]
    
    _program: Program
    _nextProcessFunction: Optional[Callable[[IncomingRequest], None]]
    _gameRoom: GameRoom
    
    _incomingMovePacket: Packet | None
    
    _tryingMove: tuple[Tuple[int, int],Tuple[int, int]]

    def __init__(self, program: Program, gameRoom: GameRoom):
        self._program = program
        self._gameRoom = gameRoom
        self._gameRoom.registerProcessingFunction(self.processIncomingMessage)
        
        self.board = [[None for _ in range(self.SIZE)] for _ in range(self.SIZE)]
        self.currentPlayer = PLAYER_COLOR.WHITE
        self.multiJumpPos = None
        self.setupInitialBoard()

    def registerProcessingFunction(self, nextProcessFunction: Callable[[IncomingRequest], None]):
        self._nextProcessFunction = nextProcessFunction
    
    def processIncomingMessage(self, incomingRequest: IncomingRequest):
        if(not self._program.ReqManager):
            Logger.LogError(CheckersBoard, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
        
        match(incomingRequest.DemandMessage.MainPacket.Opcode):
            case OPCODE.HE_MOVED:
                self._incomingMovePacket = incomingRequest.DemandMessage.MainPacket
                self._program.ReqManager.SendResponse(OPCODE.I_KNOW_HE_MOVED, [], self.onTimeout)
                self.movePiece((int(incomingRequest.DemandMessage.MainPacket.Parameters[0]), int(incomingRequest.DemandMessage.MainPacket.Parameters[1])), (int(incomingRequest.DemandMessage.MainPacket.Parameters[2]), int(incomingRequest.DemandMessage.MainPacket.Parameters[3])))
                self._gameRoom.drawBoard()
            case _:
                if(self._nextProcessFunction):
                    self._nextProcessFunction(incomingRequest)
                else:
                    raise Exception("Neznámý OPCODE")
    
    def Fejl(self):
        Logger.LogError(CheckersBoard, ERROR_CODES.SERVER_NOT_KNOW_MOVE)
    
    def TryMove(self, start: Tuple[int, int], end: Tuple[int, int]):
        if(not self._program.ReqManager):
            Logger.LogError(CheckersBoard, ERROR_CODES.OBJECT_NOT_INITIALIZED, [RequestManager.__name__])
            return
#        if(not self.isValidMove(start, end)):
#            return
        self._gameRoom.CanClick = False
        self._program.ReqManager.CreateDemand(OPCODE.I_MOVED, [str(start[0]), str(start[1]), str(end[0]), str(end[1])], self.Fejl, self.MoveRespond, OPCODE.YOU_MOVED)
        self._tryingMove = (start, end)
    
    def MoveRespond(self, responseParams: list[str]):
        self._gameRoom.CanClick = True

        if(GAME_BOOL(int(responseParams[0])) == GAME_BOOL.FALSE):
            messagebox.showwarning("Chyba", "Tah nebyl uznán.")
            return
        
        self.movePiece(self._tryingMove[0], self._tryingMove[1])
        self._gameRoom.drawBoard()
    
    def movePiece(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        p = self.board[start[0]][start[1]]
        if not p or p.owner != self.currentPlayer:
            return False
        if self.multiJumpPos and start != self.multiJumpPos:
            return False

        isCap = self.canCapture(start, end)
        if self.canAnyPieceCapture(self.currentPlayer) and not isCap:
            return False
        if not isCap and not self.isValidMove(start, end):
            return False

        if isCap:
            stepR = 1 if end[0] - start[0] > 0 else -1
            stepC = 1 if end[1] - start[1] > 0 else -1
            currR, currC = start[0] + stepR, start[1] + stepC
            while currR != end[0]:
                self.board[currR][currC] = None
                currR += stepR
                currC += stepC

        self.board[end[0]][end[1]] = self.board[start[0]][start[1]]
        self.board[start[0]][start[1]] = None

        if isCap and self.canPieceCapture(end):
            self.multiJumpPos = end
        else:
            self.promoteToKing(end)
            self.multiJumpPos = None
            self.currentPlayer = PLAYER_COLOR.BLACK if self.currentPlayer == PLAYER_COLOR.WHITE else PLAYER_COLOR.WHITE
        return True
    
    
    def onTimeout(self):
        if(not self._incomingMovePacket):
            Logger.LogError(CheckersBoard, ERROR_CODES.RESPONSE_TO_UNKNOWN_REQUEST)
            return
        
        Logger.LogError(CheckersBoard, ERROR_CODES.SERVER_NOT_KNOW_RESPONSE, [self._incomingMovePacket.CreateString()])

    def setupInitialBoard(self):
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if (r + c) % 2 != 0:
                    if r < 3:
                        self.board[r][c] = Piece(PLAYER_COLOR.BLACK, PIECE_TYPE.MAN)
                    elif r > 4:
                        self.board[r][c] = Piece(PLAYER_COLOR.WHITE, PIECE_TYPE.MAN)

    def isWithinBounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.SIZE and 0 <= c < self.SIZE

    def canCapture(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        r1, c1 = start
        r2, c2 = end
        if not self.isWithinBounds(r2, c2) or self.board[r2][c2] is not None:
            return False

        p = self.board[r1][c1]
        if not p: return False
        
        dr, dc = r2 - r1, c2 - c1

        if abs(dr) != abs(dc) or abs(dr) < 2:
            return False

        stepR = 1 if dr > 0 else -1
        stepC = 1 if dc > 0 else -1

        if p.type == PIECE_TYPE.MAN:
            # Kontrola vzdálenosti (skok o 2 pole)
            if abs(dr) != 2:
                return False
            
            # OPRAVA: Kontrola směru (bílá smí jen nahoru -2, černá jen dolů +2)
            allowedDir = -2 if p.owner == PLAYER_COLOR.WHITE else 2
            if dr != allowedDir:
                return False

            midR, midC = r1 + stepR, c1 + stepC
            target = self.board[midR][midC]
            return target is not None and target.owner != p.owner
        else:  # KING
            enemyCount = 0
            currR, currC = r1 + stepR, c1 + stepC
            while currR != r2:
                piece = self.board[currR][currC]
                if piece:
                    if piece.owner == p.owner:
                        return False
                    enemyCount += 1
                currR += stepR
                currC += stepC
            return enemyCount == 1

    def canPieceCapture(self, pos: Tuple[int, int]) -> bool:
        p = self.board[pos[0]][pos[1]]
        if not p:
            return False
        maxDist = self.SIZE if p.type == PIECE_TYPE.KING else 2
        for d in range(2, maxDist + 1):
            for dr, dc in [(d, d), (d, -d), (-d, d), (-d, -d)]:
                if self.canCapture(pos, (pos[0] + dr, pos[1] + dc)):
                    return True
        return False

    def canAnyPieceCapture(self, player: PLAYER_COLOR) -> bool:
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                piece = self.board[r][c]
                if piece and piece.owner == player and self.canPieceCapture((r, c)):
                    return True
        return False

    def isValidMove(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        r1, c1 = start
        r2, c2 = end
        if not self.isWithinBounds(r2, c2) or self.board[r2][c2] is not None:
            return False
        
        p = self.board[r1][c1]
        if not p: return False
        
        dr, dc = r2 - r1, abs(c2 - c1)

        if p.type == PIECE_TYPE.MAN:
            direction = -1 if p.owner == PLAYER_COLOR.WHITE else 1
            return dr == direction and dc == 1
        else:  # KING
            if abs(dr) != dc:
                return False
            stepR = 1 if dr > 0 else -1
            stepC = 1 if (c2 - c1) > 0 else -1
            currR, currC = r1 + stepR, c1 + stepC
            while currR != r2:
                if self.board[currR][currC]:
                    return False
                currR += stepR
                currC += stepC
            return True

    def isAnyValidMove(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """
        Vrátí True, pokud je tah z 'start' na 'end' platný podle pravidel.
        Zohledňuje prostý pohyb i braní, včetně povinnosti skákat.
        Nemění stav boardu.
        """
        r1, c1 = start
        r2, c2 = end

        # 1. Základní kontroly (v mezích, existence figurky, prázdný cíl)
        if not self.isWithinBounds(r2, c2):
            return False
        
        piece = self.board[r1][c1]
        if piece is None or self.board[r2][c2] is not None:
            return False
        
        # 2. Kontrola, zda je hráč na tahu
        if piece.owner != self.currentPlayer:
            return False

        # 3. Kontrola multi-jumpu (pokud hráč musí pokračovat stejnou figurkou)
        if self.multiJumpPos and start != self.multiJumpPos:
            return False

        # 4. Analýza typu pohybu
        is_capture = self.canCapture(start, end)
        is_regular = self.isValidMove(start, end) # Používá vaši původní logiku posunu o 1

        # 5. Pravidlo povinného braní
        # Pokud hráč může provést jakékoli braní, musí ho provést.
        if self.canAnyPieceCapture(self.currentPlayer):
            return is_capture

        # 6. Pokud není povinnost brát, stačí aby to byl buď platný posun nebo platný skok
        return is_capture or is_regular

    def promoteToKing(self, pos: Tuple[int, int]):
        piece = self.board[pos[0]][pos[1]]
        if piece and ((piece.owner == PLAYER_COLOR.WHITE and pos[0] == 0) or \
           (piece.owner == PLAYER_COLOR.BLACK and pos[0] == self.SIZE - 1)):
            piece.type = PIECE_TYPE.KING

    def printBoard(self):
        print("  0 1 2 3 4 5 6 7")
        for r in range(self.SIZE):
            rowStr = f"{r} "
            for c in range(self.SIZE):
                p = self.board[r][c]
                if not p:
                    rowStr += ". " if (r + c) % 2 != 0 else "  "
                else:
                    char = "w" if p.owner == PLAYER_COLOR.WHITE else "b"
                    if p.type == PIECE_TYPE.KING:
                        char = char.upper()
                    rowStr += char + " "
            print(rowStr + f"{r}")
        print("  0 1 2 3 4 5 6 7")
        print(f"Na tahu: {'Bila' if self.currentPlayer == PLAYER_COLOR.WHITE else 'Cerna'}")

    def isGameOver(self) -> bool:
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                p = self.board[r][c]
                if p and p.owner == self.currentPlayer:
                    if self.canPieceCapture((r, c)):
                        return False
                    for dr in [-1, 1]:
                        for dc in [-1, 1]:
                            if self.isValidMove((r, c), (r + dr, c + dc)):
                                return False
        return True

if __name__ == "__main__":
    Program().main()
"""    game = CheckersBoard()
    while not game.isGameOver():
        game.printBoard()
        try:
            inp = input("Zadej tah (r1 c1 r2 c2): ").split()
            if len(inp) != 4: break
            r1, c1, r2, c2 = map(int, inp)
            if not game.movePiece((r1, c1), (r2, c2)):
                print("--- NEPLATNY TAH! ---")
        except ValueError:
            print("Zadej cisla!")
    print("Konec hry!")"""
