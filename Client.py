import itertools

class Client:
    _id_generator = itertools.count(1)

    def __init__(self, addr: tuple):
        """addr je tuple (ip, port)"""
        self.id = next(self._id_generator)
        self.addr = addr
