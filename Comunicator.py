import socket
import threading
import queue
import time
from Logger import Logger  # <--- TENTO ŘÁDEK CHYBĚL

class Comunicator:
    def __init__(self, port):
        self.buffsize = 255
        self._running = threading.Event()
        self._running.set()
        
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.bind(('', port))
            self._sock.settimeout(0.1) 
        except Exception as e:
            # Zde se volá Logger, proto musí být nahoře naimportován
            Logger.log_error("Comunicator", f"Nelze inicializovat socket: {e}")
            raise

        Logger.log_message("Comunicator", f"Komunikátor inicializován na portu {port}")

        self._listener = self._Listener(self)
        self._sender = self._Sender(self)
    
    # ... zbytek třídy ...

    def stop(self):
        if not self._running.is_set():
            return
        
        self._running.clear()
        self._sender.stop()
        self._listener.stop()
        self._sock.close()

    def send(self, target_addr, message):
        """target_addr je tuple (ip, port)"""
        self._sender.send(target_addr, message)

    def register_receiver(self, callback):
        self._listener.register_receiver(callback)

    class _Listener:
        def __init__(self, outer):
            self.outer = outer
            self.callback = None
            self._worker = threading.Thread(target=self._main_loop, daemon=True)
            self._worker.start()

        def register_receiver(self, callback):
            if self.callback:
                Logger.log_error("Listener", "Receiver již byl registrován")
            self.callback = callback

        def stop(self):
            if self._worker.is_alive():
                self._worker.join()

        def _main_loop(self):
            while self.outer._running.is_set():
                try:
                    data, addr = self.outer._sock.recvfrom(self.outer.buffsize)
                    message = data.decode('utf-8')
                    
                    Logger.log_message("Comunicator", f"Přijmuta zpráva: \"{message}\" z {addr}")
                    
                    if self.callback:
                        self.callback(addr, message)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.outer._running.is_set():
                        Logger.log_error("Comunicator", f"Fatální chyba socketu: {e}")
                    break

    class _Sender:
        def __init__(self, outer):
            self.outer = outer
            self._queue = queue.Queue()
            self._worker = threading.Thread(target=self._main_loop, daemon=True)
            self._worker.start()

        def send(self, target_addr, message):
            self._queue.put((target_addr, message))

        def stop(self):
            self._queue.put(None)
            if self._worker.is_alive():
                self._worker.join()

        def _main_loop(self):
            while True:
                item = self._queue.get()
                if item is None: break
                
                addr, msg = item
                try:
                    Logger.log_message("Comunicator", f"Odesílání: \"{msg}\" na {addr}")
                    sent = self.outer._sock.sendto(msg.encode('utf-8'), addr)
                    if sent != len(msg):
                        Logger.log_error("Comunicator", "Nepodařilo se odeslat celou zprávu")
                except Exception as e:
                    Logger.log_error("Comunicator", f"Chyba při odesílání: {e}")
                
                self._queue.task_done()
