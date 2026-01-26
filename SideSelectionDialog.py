import tkinter as tk
from typing import Optional, Callable
from GAME_BOOL import PLAYER_COLOR

class SideSelectionDialog:
    # Definice členských proměnných s typy
    _parent: tk.Tk
    _onSubmitCallback: Callable[[PLAYER_COLOR], None]
    _window: Optional[tk.Toplevel]
    _btnFrame: Optional[tk.Frame]

    def __init__(self, parent: tk.Tk, onSubmitCallback: Callable[[PLAYER_COLOR], None]):
        self._parent = parent
        self._onSubmitCallback = onSubmitCallback
        self._window = None
        self._btnFrame = None

    def Show(self) -> None:
        self._window = tk.Toplevel(self._parent)
        self._window.title("Vyberte stranu")
        self._window.geometry("250x100")
        self._window.grab_set()

        tk.Label(self._window, text="Za koho chcete hrát?").pack(pady=10)

        self._btnFrame = tk.Frame(self._window)
        self._btnFrame.pack(pady=5)

        tk.Button(self._btnFrame, text="Bílý", width=8, 
                  command=lambda: self.Submit(PLAYER_COLOR.WHITE)).pack(side="left", padx=5)
        tk.Button(self._btnFrame, text="Černý", width=8, 
                  command=lambda: self.Submit(PLAYER_COLOR.BLACK)).pack(side="left", padx=5)
        tk.Button(self._btnFrame, text="Zrušit", width=8, 
                  command=self._window.destroy).pack(side="left", padx=5)

    def Submit(self, side: PLAYER_COLOR) -> None:
        self._onSubmitCallback(side)
        
        if self._window:
            self._window.destroy()
