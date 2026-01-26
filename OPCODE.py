from enum import IntEnum


class OPCODE(IntEnum):
    TEST = 0
    PING = 1

    ACK = 2

    CON = 4
    CON_AS = 5

    WANA_NAME = 6
    VALID_NAME = 7

    WANA_ROOMS = 8
    ROOM_LIST = 9

    CREATE_ROOM = 10
    ROOM_CREATED = 11
    
    GET_TO_ROOM = 12
    GOT_TO_ROOM = 13

    OPPONENT_ARRIVED = 14
    KNOW_ABOUT_HIM = 15
    
    I_MOVED = 16
    YOU_MOVED = 17
    
    HE_MOVED = 18
    I_KNOW_HE_MOVED = 19
    
    GAME_FINISHED = 20
    FINALY_END = 21

    AM_LEAVING = 22
    YOU_LEFT = 23

    GAME_QUIT = 24
    GAME_QUITED = 25
