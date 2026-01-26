# type: ignore
import time
import sys

# Importy vašich modulů
from Logger import Logger, LogLevel
from Comunicator import Comunicator
from MessageManager import MessageManager
from Message import IncomingMessage
from Packet import Packet, Origin, Opcode

def process_incoming_message(in_msg: IncomingMessage):
    packet = in_msg.MainPacket
    print(f"Přijat packet ID: {packet.id}, Opcode: {packet.opcode}")

def main():
    # Nyní bude Logger definován díky importu výše
    if not Logger.init("app_log.txt"):
        print("Nepodařilo se inicializovat Logger.")
        sys.exit(1)

    try:
        comunicator = Comunicator(port=7890)
        manager = MessageManager()
        
        manager._processing_function = process_incoming_message
        manager.ConnectToComunicator(comunicator, 2000, 3)

        Logger.LogMessage("Main", "Systém běží...")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        Logger.LogMessage("Main", "Ukončování...")
    finally:
        Logger.terminate()

if __name__ == "__main__":
    main()
