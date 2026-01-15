from __future__ import annotations
import threading
from typing import Callable, Optional, TYPE_CHECKING

# Importujeme pouze pro statickou analýzu, za běhu se tento blok nevykoná
if TYPE_CHECKING:
    from Packet import Packet
    from MessageManager import MessageManager

class IncomingMessage:
    def __init__(self, packet: Packet, addr: tuple):
        self.main_packet = packet
        self.client_address = addr

class OutgoingMessage:
    def __init__(self, packet: Packet, addr: tuple, on_timeout: Callable):
        self.main_packet = packet
        self.client_address = addr
        self._on_timeout = on_timeout
        self._running = threading.Event()
        self._finished = threading.Event()
        self._attempts = 0
        self._timeout = 1.0
        self._max_attempts = 3
        self._message_manager = None # Typ určíme jen v anotaci níže
        self._worker: Optional[threading.Thread] = None

    def register_manager(self, manager: MessageManager, timeout: int, max_attempts: int):
        self._message_manager = manager
        self._timeout = timeout / 1000.0
        self._max_attempts = max_attempts

    def on_message_sent(self):
        self._attempts += 1
        self._running.set()
        self._worker = threading.Thread(target=self._wait_for_ack, daemon=True)
        self._worker.start()

    def finish(self):
        self._finished.set()

    def _wait_for_ack(self):
        while self._running.is_set() and not self._finished.is_set():
            if self._finished.wait(self._timeout):
                return
            if self._attempts >= self._max_attempts:
                break
            self._attempts += 1
            if self._message_manager:
                self._message_manager.send_packet(self.client_address, self.main_packet)
        if not self._finished.is_set():
            self._on_timeout()
