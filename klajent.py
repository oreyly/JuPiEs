import time
from Logger import Logger
from Comunicator import Comunicator
from MessageManager import MessageManager
from RequestManager import RequestManager
from Packet import Opcode
from Client import Client

def main():
    Logger.init("client_log.txt")

    try:
        # Klient běží na jiném portu (např. 7891), aby nekolidoval na stejném PC
        comunicator = Comunicator(port=7891)
        
        msg_manager = MessageManager()
        msg_manager.connect_to_comunicator(comunicator, timeout_ms=2000, max_attempts=3)

        req_manager = RequestManager()
        req_manager.connect_to_message_manager(msg_manager)

        # Definice cíle (C++ Server)
        server_node = Client(addr=("10.0.1.72", 7890))

        def success(): print(">>> Python Client: Požadavek serverem potvrzen a zpracován!")
        def failure(): print(">>> Python Client: Server neodpovídá.")

        print("Posílám požadavek na C++ Server...")
        req_manager.create_demand(
            client=server_node,
            opcode=Opcode.ACK,        # Příklad opcodu
            params=["DataZPythonu"], 
            timeout=5000, 
            on_failure=failure, 
            on_success=success, 
            expected_opcode=Opcode.ACK
        )

        # Necháme klienta chvíli běžet, aby stihl přijmout odpověď
        time.sleep(10)

    finally:
        req_manager.stop()
        msg_manager.stop()
        comunicator.stop()
        Logger.terminate()

if __name__ == "__main__":
    main()
