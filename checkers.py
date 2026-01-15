from enum import Enum
from typing import Optional, List, Tuple

class Player(Enum):
    WHITE = 1
    BLACK = 2

class PieceType(Enum):
    MAN = 1
    KING = 2

class Piece:
    def __init__(self, owner: Player, piece_type: PieceType):
        self.owner = owner
        self.type = piece_type

class CheckersBoard:
    SIZE = 8

    def __init__(self):
        self.board: List[List[Optional[Piece]]] = [[None for _ in range(self.SIZE)] for _ in range(self.SIZE)]
        self.current_player = Player.WHITE
        self.multi_jump_pos: Optional[Tuple[int, int]] = None
        self._setup_initial_board()

    def _setup_initial_board(self):
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if (r + c) % 2 != 0:
                    if r < 3:
                        self.board[r][c] = Piece(Player.BLACK, PieceType.MAN)
                    elif r > 4:
                        self.board[r][c] = Piece(Player.WHITE, PieceType.MAN)

    def is_within_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.SIZE and 0 <= c < self.SIZE

    def can_capture(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        r1, c1 = start
        r2, c2 = end
        if not self.is_within_bounds(r2, c2) or self.board[r2][c2] is not None:
            return False

        p = self.board[r1][c1]
        dr, dc = r2 - r1, c2 - c1

        if abs(dr) != abs(dc) or abs(dr) < 2:
            return False

        step_r = 1 if dr > 0 else -1
        step_c = 1 if dc > 0 else -1

        if p.type == PieceType.MAN:
            if abs(dr) != 2:
                return False
            mid_r, mid_c = r1 + step_r, c1 + step_c
            target = self.board[mid_r][mid_c]
            return target is not None and target.owner != p.owner
        else:  # KING
            enemy_count = 0
            curr_r, curr_c = r1 + step_r, c1 + step_c
            while curr_r != r2:
                piece = self.board[curr_r][curr_c]
                if piece:
                    if piece.owner == p.owner:
                        return False
                    enemy_count += 1
                curr_r += step_r
                curr_c += step_c
            return enemy_count == 1

    def can_piece_capture(self, pos: Tuple[int, int]) -> bool:
        p = self.board[pos[0]][pos[1]]
        if not p:
            return False
        max_dist = self.SIZE if p.type == PieceType.KING else 3 # 2 pole pro skok, 3 pro range kontroly
        for d in range(2, max_dist + 1):
            for dr, dc in [(d, d), (d, -d), (-d, d), (-d, -d)]:
                if self.can_capture(pos, (pos[0] + dr, pos[1] + dc)):
                    return True
        return False

    def can_any_piece_capture(self, player: Player) -> bool:
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                piece = self.board[r][c]
                if piece and piece.owner == player and self.can_piece_capture((r, c)):
                    return True
        return False

    def is_valid_move(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        r1, c1 = start
        r2, c2 = end
        if not self.is_within_bounds(r2, c2) or self.board[r2][c2] is not None:
            return False
        
        p = self.board[r1][c1]
        dr, dc = r2 - r1, abs(c2 - c1)

        if p.type == PieceType.MAN:
            direction = -1 if p.owner == Player.WHITE else 1
            return dr == direction and dc == 1
        else:  # KING
            if abs(dr) != dc:
                return False
            step_r = 1 if dr > 0 else -1
            step_c = 1 if (c2 - c1) > 0 else -1
            curr_r, curr_c = r1 + step_r, c1 + step_c
            while curr_r != r2:
                if self.board[curr_r][curr_c]:
                    return False
                curr_r += step_r
                curr_c += step_c
            return True

    def move_piece(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        p = self.board[start[0]][start[1]]
        if not p or p.owner != self.current_player:
            return False
        if self.multi_jump_pos and start != self.multi_jump_pos:
            return False

        is_cap = self.can_capture(start, end)
        if self.can_any_piece_capture(self.current_player) and not is_cap:
            return False
        if not is_cap and not self.is_valid_move(start, end):
            return False

        # Provedení pohybu a braní
        if is_cap:
            step_r = 1 if end[0] - start[0] > 0 else -1
            step_c = 1 if end[1] - start[1] > 0 else -1
            curr_r, curr_c = start[0] + step_r, start[1] + step_c
            while curr_r != end[0]:
                self.board[curr_r][curr_c] = None
                curr_r += step_r
                curr_c += step_c

        self.board[end[0]][end[1]] = self.board[start[0]][start[1]]
        self.board[start[0]][start[1]] = None

        if is_cap and self.can_piece_capture(end):
            self.multi_jump_pos = end
        else:
            self._promote_to_king(end)
            self.multi_jump_pos = None
            self.current_player = Player.BLACK if self.current_player == Player.WHITE else Player.WHITE
        return True

    def _promote_to_king(self, pos: Tuple[int, int]):
        piece = self.board[pos[0]][pos[1]]
        if (piece.owner == Player.WHITE and pos[0] == 0) or \
           (piece.owner == Player.BLACK and pos[0] == self.SIZE - 1):
            piece.type = PieceType.KING

    def print_board(self):
        print("  0 1 2 3 4 5 6 7")
        for r in range(self.SIZE):
            row_str = f"{r} "
            for c in range(self.SIZE):
                p = self.board[r][c]
                if not p:
                    row_str += ". " if (r + c) % 2 != 0 else "  "
                else:
                    char = "w" if p.owner == Player.WHITE else "b"
                    if p.type == PieceType.KING:
                        char = char.upper()
                    row_str += char + " "
            print(row_str + f"{r}")
        print("  0 1 2 3 4 5 6 7")
        print(f"Na tahu: {'Bila' if self.current_player == Player.WHITE else 'Cerna'}")

    def is_game_over(self) -> bool:
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                p = self.board[r][c]
                if p and p.owner == self.current_player:
                    if self.can_piece_capture((r, c)):
                        return False
                    for dr in [-1, 1]:
                        for dc in [-1, 1]:
                            if self.is_valid_move((r, c), (r + dr, c + dc)):
                                return False
        return True

if __name__ == "__main__":
    game = CheckersBoard()
    while not game.is_game_over():
        game.print_board()
        try:
            inp = input("Zadej tah (r1 c1 r2 c2): ").split()
            if len(inp) != 4: break
            r1, c1, r2, c2 = map(int, inp)
            if not game.move_piece((r1, c1), (r2, c2)):
                print("--- NEPLATNY TAH! ---")
        except ValueError:
            print("Zadej cisla!")
    print("Konec hry!")
