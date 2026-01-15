import tkinter as tk
from tkinter import messagebox
from checkers import CheckersBoard, Player, PieceType  # Předpokládá předchozí kód v checkers.py

class CheckersGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Dáma - Python")
        self.game = CheckersBoard()
        
        self.cell_size = 80
        self.canvas = tk.Canvas(
            root, 
            width=self.game.SIZE * self.cell_size, 
            height=self.game.SIZE * self.cell_size
        )
        self.canvas.pack()
        
        self.selected_pos = None
        self.canvas.bind("<Button-1>", self.on_click)
        
        self.draw_board()

    def draw_board(self):
        self.canvas.delete("all")
        for r in range(self.game.SIZE):
            for c in range(self.game.SIZE):
                # Vykreslení čtverců
                x1, y1 = c * self.cell_size, r * self.cell_size
                x2, y2 = x1 + self.cell_size, y1 + self.cell_size
                color = "#DDBB99" if (r + c) % 2 == 0 else "#663300"
                
                # Zvýraznění vybraného pole
                if self.selected_pos == (r, c):
                    color = "#AAFF22"
                
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")

                # Vykreslení figurky
                piece = self.game.board[r][c]
                if piece:
                    self.draw_piece(r, c, piece)

    def draw_piece(self, r, c, piece):
        padding = 10
        x1, y1 = c * self.cell_size + padding, r * self.cell_size + padding
        x2, y2 = (c + 1) * self.cell_size - padding, (r + 1) * self.cell_size - padding
        
        fill_color = "white" if piece.owner == Player.WHITE else "#222222"
        outline_color = "black" if piece.owner == Player.WHITE else "white"
        
        self.canvas.create_oval(x1, y1, x2, y2, fill=fill_color, outline=outline_color, width=2)
        
        # Označení Dámy (King)
        if piece.type == PieceType.KING:
            self.canvas.create_text(
                (x1 + x2) / 2, (y1 + y2) / 2, 
                text="K", fill="gold", font=("Arial", 24, "bold")
            )

    def on_click(self, event):
        col = event.x // self.cell_size
        row = event.y // self.cell_size
        clicked_pos = (row, col)

        if self.selected_pos is None:
            # Výběr figurky
            piece = self.game.board[row][col]
            if piece and piece.owner == self.game.current_player:
                self.selected_pos = clicked_pos
        else:
            # Pokus o tah
            if self.game.move_piece(self.selected_pos, clicked_pos):
                # Pokud po skoku může stejná figurka skákat znovu, zůstane vybraná
                if self.game.multi_jump_pos:
                    self.selected_pos = self.game.multi_jump_pos
                else:
                    self.selected_pos = None
            else:
                # Změna výběru nebo zrušení
                piece = self.game.board[row][col]
                if piece and piece.owner == self.game.current_player:
                    self.selected_pos = clicked_pos
                else:
                    self.selected_pos = None

        self.draw_board()
        
        if self.game.is_game_over():
            winner = "Černá" if self.game.current_player == Player.WHITE else "Bílá"
            messagebox.showinfo("Konec hry", f"Hra skončila! Vítěz: {winner}")
            self.game = CheckersBoard()
            self.draw_board()

if __name__ == "__main__":
    root = tk.Tk()
    gui = CheckersGUI(root)
    root.mainloop()
