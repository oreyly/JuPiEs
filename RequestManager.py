from typing import Callable, Optional, Dict, List
import threading
import queue
from typing import Dict, List, Optional
from MessageManager import MessageManager
from Message import IncomingMessage
from Request import IncomingRequest, OutgoingRequest
from Logger import Logger

class RequestManager:
    def __init__(self):
        self._processing_function: Optional[Callable] = None
        self._our_demands: Dict[int, List[OutgoingRequest]] = {} # ID zprávy -> List requestů
        self._incoming_queue = queue.Queue()
        self._message_manager: Optional[MessageManager] = None
        self._running = threading.Event()
        self._lock = threading.Lock()
        self._worker: Optional[threading.Thread] = None

    def connect_to_message_manager(self, message_manager: MessageManager):
        self._message_manager = message_manager
        self._running.set()
        self._worker = threading.Thread(target=self._main_loop, daemon=True)
        self._worker.start()
        
        # Registrace callbacku pro příjem zpráv
        self._message_manager.register_processing_function(self._on_message_receive)

    def create_demand(self, client, opcode, params, timeout, on_failure, on_success, expected_opcode):
        req = OutgoingRequest(client, opcode, params, timeout, on_failure, on_success, expected_opcode)
        
        with self._lock:
            msg_id = req.demand_message.main_packet.id
            if msg_id not in self._our_demands:
                self._our_demands[msg_id] = []
            self._our_demands[msg_id].append(req)
        
        if self._message_manager:
            self._message_manager.send_message(req.demand_message)
            req.on_request_sent()

    def _on_message_receive(self, incoming_message: IncomingMessage):
        if self._running.is_set():
            self._incoming_queue.put(incoming_message)

    def _main_loop(self):
        while self._running.is_set():
            try:
                msg = self._incoming_queue.get(timeout=0.1)
                
                # Zkusíme spárovat příchozí zprávu s našimi požadavky
                found_demand = False
                with self._lock:
                    msg_id = msg.main_packet.id
                    if msg_id in self._our_demands:
                        # Validujeme všechny requesty čekající na toto ID
                        for req in self._our_demands[msg_id]:
                            if req.validate_incoming_message(msg):
                                found_demand = True
                        
                        # Po vyřízení (úspěch/fail) odstraníme z mapy
                        del self._our_demands[msg_id]

                # Pokud to není odpověď na náš požadavek, je to nový příchozí požadavek
                if not found_demand and self._processing_function:
                    p = msg.main_packet
                    inc_req = IncomingRequest(p.client_id, msg.client_address, p.opcode, p.parameters)
                    self._processing_function(inc_req)

            except queue.Empty:
                continue

    def register_processing_function(self, func: Callable):
        self._processing_function = func

    def stop(self):
        self._running.clear()
        if self._worker:
            self._worker.join()
