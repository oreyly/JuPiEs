import threading
import queue
import time
from collections import deque
from Message import IncomingMessage, OutgoingMessage
from Packet import Packet, Opcode, Origin
from Logger import Logger

class MessageManager:
    CLEANER_SLEEP_SEC = 1.0
    HISTORY_LIMIT_SEC = 60.0

    def __init__(self):
        self._running = threading.Event()
        self._comunicator = None
        self._processing_function = None  # Zde se ukládá callback
        
        self._outgoing_messages = {}
        self._arrived_queue = queue.Queue()
        
        self._finished_history = deque()
        self._finished_map = {}
        
        self._lock_outgoing = threading.Lock()
        self._lock_finished = threading.Lock()

        self._message_worker = None
        self._cleaning_worker = None
        Logger.log_message("MessageManager", "Vytvořen MessageManager.")

    # Přidaná metoda, která chyběla
    def register_processing_function(self, processing_function):
        if self._processing_function:
            Logger.log_error("MessageManager", "Objekt již byl registrován.")
        self._processing_function = processing_function

    def connect_to_comunicator(self, comunicator, timeout_ms, max_attempts):
        self._comunicator = comunicator
        self._running.set()
        self._message_timeout = timeout_ms
        self._max_attempts = max_attempts
        self._cleaning_worker = threading.Thread(target=self._cleaning_loop, daemon=True)
        self._message_worker = threading.Thread(target=self._main_loop, daemon=True)
        self._cleaning_worker.start()
        self._message_worker.start()
        self._comunicator.register_receiver(self._on_string_receive)

    def _on_string_receive(self, addr, message_str):
        if self._running.is_set():
            self._arrived_queue.put((addr, message_str))

    def _main_loop(self):
        while self._running.is_set():
            try:
                addr, msg_str = self._arrived_queue.get(timeout=0.1)
                packet = Packet(raw_msg=msg_str)
                if not packet.is_valid:
                    continue

                if packet.opcode == Opcode.ACK:
                    with self._lock_outgoing:
                        if packet.id in self._outgoing_messages:
                            msg = self._outgoing_messages.pop(packet.id)
                            msg.finish()
                    continue

                if packet.id in self._finished_map:
                    continue

                in_msg = IncomingMessage(packet, addr)
                self._confirm_receiving(in_msg)
                
                # Volání registrovaného callbacku
                if self._processing_function:
                    self._processing_function(in_msg)

            except queue.Empty:
                continue

    def _confirm_receiving(self, in_msg: IncomingMessage):
        ack_packet = Packet(target_id=in_msg.main_packet.id, origin=Origin.SERVER, opcode=Opcode.ACK)
        self.send_packet(in_msg.client_address, ack_packet)

    def send_packet(self, addr, packet: Packet):
        if self._comunicator:
            self._comunicator.send(addr, packet.create_string())

    def _cleaning_loop(self):
        while self._running.is_set():
            time.sleep(self.CLEANER_SLEEP_SEC)
            self._clean_finished()

    def _clean_finished(self):
        now = time.time()
        with self._lock_finished:
            while self._finished_history and (now - self._finished_history[0][1]) > self.HISTORY_LIMIT_SEC:
                old_id, _ = self._finished_history.popleft()
                self._finished_map.pop(old_id, None)

    def stop(self):
        self._running.clear()
        if self._message_worker: self._message_worker.join()
        if self._cleaning_worker: self._cleaning_worker.join()
        
    def send_message(self, outgoing_message: OutgoingMessage):
        with self._lock_outgoing:
            # Předá zprávě nastavení timeoutu a pokusů z manažera
            outgoing_message.register_manager(
                self, 
                self._message_timeout, 
                self._max_attempts
            )
            
            # Uloží zprávu pro budoucí zpracování ACK
            self._outgoing_messages[outgoing_message.main_packet.id] = outgoing_message
            
            # Fyzicky odešle packet přes komunikátor
            self.send_packet(outgoing_message.client_address, outgoing_message.main_packet)
            
            # Spustí vlákno, které hlídá doručení (retransmise)
            outgoing_message.on_message_sent()
