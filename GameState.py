from enum import IntEnum

class GAME_STATE(IntEnum):
	IN_PROGRESS = 0
	WHITE_WIN = 1
	BLACK_WIN = 2
	DRAW = 3
	PRE_GAME = 4
