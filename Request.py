import threading
import time
from typing import Callable, List, Optional
from Message import OutgoingMessage, IncomingMessage
from Packet import Packet, Origin

class IncomingRequest:
    def __init__(self, client_id: int, source_addr: tuple, opcode, params: List[str]):
        self.client_id = client_id
        self.source_address = source_addr
        self.opcode = opcode
        self.parameters = params

class OutgoingRequest:
    def __init__(self, client, opcode, params: List[str], timeout: int, 
                 on_failure: Callable, on_success: Callable, expected_opcode):
        self._timeout = timeout / 1000.0
        self._on_failure = on_failure
        self._on_success = on_success
        self._expected_opcode = expected_opcode
        
        self._waiting = threading.Event()
        self._has_result = False
        self.response_message: Optional[IncomingMessage] = None
        
        # Vytvoření základní odchozí zprávy
        p = Packet(target_id=client.id, origin=Origin.SERVER, opcode=opcode, params=params)
        self.demand_message = OutgoingMessage(p, client.addr, self._handle_timeout)
        self._worker: Optional[threading.Thread] = None

    def _handle_timeout(self):
        if not self._has_result:
            self._waiting.clear()
            self._on_failure()

    def on_request_sent(self):
        self._waiting.set()
        self._worker = threading.Thread(target=self._wait_for_response, daemon=True)
        self._worker.start()

    def _wait_for_response(self):
        # Čekání na událost nebo timeout
        if not self._waiting.wait(self._timeout):
            if not self._has_result:
                self._waiting.clear()
                self._on_failure()
                return

        if self._has_result:
            self._on_success()

    def validate_incoming_message(self, incoming_message: IncomingMessage) -> bool:
        if not self._waiting.is_set():
            return False

        # Kontrola, zda ID a Opcode odpovídají očekávání
        is_valid = (incoming_message.main_packet.id == self.demand_message.main_packet.id and 
                    incoming_message.main_packet.opcode == self._expected_opcode)

        if is_valid:
            self.response_message = incoming_message
            self._has_result = True
            self._waiting.clear() # Signalizace pro worker thread
        
        return is_valid

    def stop(self):
        self._waiting.clear()
        if self._worker and self._worker.is_alive():
            self._worker.join()
