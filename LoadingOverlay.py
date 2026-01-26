import tkinter as tk

class LoadingOverlay:
    def __init__(self, parent: tk.Misc, message: str = "Pracuji..."):
        self.parent = parent
        # Toplevel okno
        self.window = tk.Toplevel(parent)
        self.window.withdraw() # Skryjeme před nastavením pozice
        
        # Nastavení vzhledu
        self.window.overrideredirect(True) # Odstraní horní lištu (vypadá to jako čistý overlay)
        self.window.configure(bg="#2C3E50", highlightbackground="#3498DB", highlightthickness=2)
        
        # Udělá okno modální
        self.window.transient(parent) # type: ignore
        self.window.grab_set()

        # Obsah
        self.label = tk.Label(self.window, text=message, bg="#2C3E50", fg="white", font=("Arial", 10, "bold"))
        self.label.pack(pady=(15, 5), padx=20)
        
        self.spinner = tk.Label(self.window, text="|", bg="#2C3E50", fg="#3498DB", font=("Consolas", 20))
        self.spinner.pack(pady=(0, 15))

        self._chars = ["|", "/", "-", "\\"]
        self._index = 0
        
        # Vycentrování a zobrazení
        self._center_window()
        self.window.deiconify()
        self._animate()

    def _center_window(self):
        self.window.update_idletasks()
        # Získání rozměrů rodiče
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        
        # Rozměry overlaye
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        
        # Výpočet středu
        x = parent_x + (parent_w // 2) - (w // 2)
        y = parent_y + (parent_h // 2) - (h // 2)
        
        self.window.geometry(f"+{x}+{y}")

    def _animate(self):
        if self.window.winfo_exists():
            self.spinner.config(text=self._chars[self._index % 4])
            self._index += 1
            self.window.after(100, self._animate)

    def stop(self):
        if self.window.winfo_exists():
            self.window.grab_release()
            self.window.destroy()
