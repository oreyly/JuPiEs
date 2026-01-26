import threading
import time
import tkinter as tk
import random

def zobraz_vtipny_vysledek(vysledek):
    popup = tk.Toplevel()
    popup.title("Dáma hlásí...")
    popup.geometry("350x200")
    popup.resizable(False, False)
    
    # Definice vtipných hlášek
    hlasky = {
        "výhra": [
            "Tvoje dáma právě provedla vítězný tanec!",
            "Soupeřovy figurky šly dobrovolně do krabice.",
            "Gratuluji, tvoje IQ právě stouplo o 2 políčka!"
        ],
        "prohra": [
            "Tvoje figurky byly vyslány na dovolenou... mimo šachovnici.",
            "Tohle nebyla prohra, to byl strategický ústup do krabice.",
            "I dřevěná figurka má někdy špatný den."
        ],
        "remíza": [
            "Nikdo nevyhrál, figurky se dohodly na příměří.",
            "Patová situace. Figurky odmítají dál skákat.",
            "Smírná dohoda. Jděte radši na kafe."
        ]
    }

    text_hlasky = random.choice(hlasky.get(vysledek, ["Něco se stalo..."]))
    
    # Barvy podle výsledku
    barvy = {
        "výhra": "#4CAF50",
        "prohra": "#F44336",
        "remíza": "#FF9800"
    }
    color = barvy.get(vysledek, "gray")

    popup.configure(bg=color)

    # Obsah
    tk.Label(popup, text=str(vysledek).upper(), font=("Comic Sans MS", 20, "bold"), 
             bg=color, fg="white").pack(pady=10)
    
    label_msg = tk.Label(popup, text=text_hlasky, font=("Arial", 11, "italic"), 
                         bg=color, fg="white", wraplength=300)
    label_msg.pack(pady=10)

    # Jednoduchá animace "poskočení" okna
    def shake(count=0):
        if count < 10:
            x = popup.winfo_x()
            y = popup.winfo_y()
            shift = 5 if count % 2 == 0 else -5
            popup.geometry(f"+{x+shift}+{y}")
            popup.after(50, lambda: shake(count + 1))

    tk.Button(popup, text="Beru na vědomí", command=popup.destroy, 
              relief="flat", bg="white").pack(pady=10)
    
    popup.after(100, shake)

zobraz_vtipny_vysledek("remíza")
