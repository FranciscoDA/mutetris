#! /usr/bin/env python3

import sys
import os
import select
import time
import random
from enum import Enum

class Col(Enum):
	red="\033[48;5;9m"
	grn="\033[48;5;10m"
	ylw="\033[48;5;11m"
	blu="\033[48;5;12m"
	pur="\033[48;5;13m"
	cyn="\033[48;5;14m"
	org="\033[48;5;202m"

ANSI_reset = "\033[0m"
ANSI_clear_all = '\033[2J'
ANSI_clear_above = '\033[0J'
ANSI_clear_below = '\033[1J'
ANSI_cursor_position = lambda row,col: '\033[' + str(row) + ';' + str(col) + 'H'

board_w = 10
board_h = 20

pieces = [ # all piece types are defined as a square map of objects
	[
		None,    None,    Col.red, None,
		None,    None,    Col.red, None,
		None,    None,    Col.red, None,
		None,    None,    Col.red, None,
	],
	[
		Col.ylw, Col.ylw, None,
		Col.ylw, None,    None,
		Col.ylw, None,    None,
	],
	[
		None,    Col.pur, Col.pur,
		None,    None,    Col.pur,
		None,    None,    Col.pur,
	],
	[
		Col.blu, Col.blu,
		Col.blu, Col.blu,
	],
	[
		None,    Col.grn, None,
		Col.grn, Col.grn, Col.grn,
		None,    None,    None,
	],
	[
		None,    Col.cyn, Col.cyn,
		Col.cyn, Col.cyn, None,
		None,    None,    None,
	],
	[
		Col.org, Col.org, None,
		None,    Col.org, Col.org,
		None,    None,    None,
	],
]
piece_size = lambda piece_type: int(len(piece_type)**0.5)

def draw(board, piece_type, piece_x, piece_y, piece_r, piece_next, player_score):
	buf = ANSI_cursor_position(1,1)
	block_width = 2
	active_block = '\033[38;5;7m(\033[38;5;0m)'
	inactive_block = active_block
	blank = '  '
	shadow = '()'
	shadow_x, shadow_y = piece_x, piece_y
	while canmove(board, piece_type, shadow_x, shadow_y+1, piece_r):
		shadow_y += 1

	# draw the main area
	for y in range(board_h):
		for x in range(board_w):
			ch = board[y*board_w+x]
			if ch:
				buf += ch.value + inactive_block + ANSI_reset
			else:
				ch = getpieceblock(piece_type, x-piece_x, y-piece_y, piece_r)
				if ch:
					buf += ch.value + active_block + ANSI_reset
				else:
					ch = getpieceblock(piece_type, x-shadow_x, y-shadow_y, piece_r)
					if ch:
						buf += shadow
					else:
						buf += blank
		buf += '|\n'

	# draw the next piece
	buf += ANSI_cursor_position(2, (board_w+1)*block_width+1) + 'Next:'
	for py in range(5):
		buf += ANSI_cursor_position(3+py, (board_w+1) * block_width + 1)
		for px in range(5):
			ch = getpieceblock(piece_next, px, py, 0)
			if ch is not None:
				buf += ch.value + active_block + ANSI_reset
			else:
				buf += blank

	# draw the score
	buf += ANSI_cursor_position(12, (board_w+1)*block_width+1)
	buf += 'Score: ' + str(player_score)
	buf += ANSI_cursor_position(board_h+1, 1)

	# write buffer to stdout
	print(buf, end='', flush=True)

def getinput(timeout):
	import tty
	import termios
	try:
		oldattrs = termios.tcgetattr(sys.stdin.fileno())
		tty.setraw(sys.stdin.fileno())
		ready = select.select([sys.stdin], [], [], timeout)
		if sys.stdin in ready[0]:
			x = sys.stdin.buffer.read1(4)
			return x
		return None
	finally:
		termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, oldattrs)

def canmove(board, piece_type, piece_x, piece_y, piece_r):
	return all(
		pblk is None or 0 <= px+piece_x < board_w and py+piece_y < board_h and board[(py+piece_y)*board_w+px+piece_x] is None
		for px, py, pblk in iterpieceblocks(piece_type, piece_r)
	)

def getpieceblock(piece_type, px, py, piece_r):
	# get a block inside a (possibly rotated) piece from
	# the px,py coordinates, which are relative to the top-left of the piece
	sz = piece_size(piece_type)
	if px < 0 or px >= sz or py < 0 or py >= sz:
		return None
	if piece_r == 0:   return piece_type[py*sz+px]
	elif piece_r == 1: return piece_type[(sz-px-1)*sz+py]
	elif piece_r == 2: return piece_type[(sz-py-1)*sz+(sz-px-1)]
	else:              return piece_type[px*sz+(sz-py-1)]

def iterpieceblocks(piece_type, piece_r):
	# iterate all the sub blocks of a piece
	return (
		(px, py, getpieceblock(piece_type, px, py, piece_r))
		for py in range(piece_size(piece_type)) for px in range(piece_size(piece_type))
	)

# decrease the input timer multiplicatively for every 100 points
input_bucket_max = lambda player_score: 0.85 ** (player_score // 100)

KEY_LEFT = b'\x1b[D' # left arrow
KEY_RIGHT = b'\x1b[C' # right arrow
KEY_DOWN = b'\x1b[B' # down arrow
KEY_UP = b'\x1b[A' # up arrow
KEY_QUIT = b'\x1b' # esc
KEY_SPACEBAR = b' '

if __name__ == '__main__':
	random.seed(time.time())
	board = [None for i in range(board_w*board_h)]
	exit = False

	player_score = 0
	piece_counter = 1
	piece_type = random.choice(pieces)
	piece_x, piece_y, piece_r = board_w//2 - piece_size(piece_type)//2, 0, 0
	piece_next = random.choice(pieces)

	input_bucket = input_bucket_max(player_score)
	print(ANSI_clear_all, flush=True)
	while not exit:
		draw(board, piece_type, piece_x, piece_y, piece_r, piece_next, player_score)
		t = time.time()
		inp = getinput(max(0, input_bucket))
		# deduct the elapsed time from the bucket
		input_bucket -= time.time() - t
		if inp == KEY_QUIT:
			exit = True
		elif inp == KEY_LEFT and canmove(board, piece_type, piece_x-1, piece_y, piece_r):
			piece_x -= 1
		elif inp == KEY_RIGHT and canmove(board, piece_type, piece_x+1, piece_y, piece_r):
			piece_x += 1
		elif inp == KEY_UP:
			for x in [0, -1, 1]:
				if canmove(board, piece_type, piece_x+x, piece_y, (piece_r+1)%4):
					piece_r = (piece_r+1) % 4
					piece_x += x
					break
		else:
			max_drop = 0
			if inp == KEY_DOWN or inp == None:
				max_drop = 1
			elif inp == KEY_SPACEBAR:
				max_drop = board_h
			for _ in range(max_drop):
				if canmove(board, piece_type, piece_x, piece_y + 1, piece_r):
					piece_y += 1
				else:
					if piece_y <= 0:
						exit = True
					for px, py, pblk in iterpieceblocks(piece_type, piece_r):
						if pblk is not None:
							board[(py+piece_y)*board_w+px+piece_x] = pblk
					piece_type = piece_next
					piece_x, piece_y, piece_r = board_w//2 - piece_size(piece_type)//2, 0, 0
					piece_next = random.choice(pieces)
					piece_counter += 1
					if piece_counter % 5 == 0:
						random.seed(time.time())
					multiplier = 1
					# check for a complete row and clear it
					for y in range(board_h):
						if all(board[y*board_w+x] is not None for x in range(board_w)):
							board[board_w:(y+1)*board_w] = board[0:y*board_w]
							board[0:board_w] = [None] * board_w
							player_score += board_w * multiplier
							multiplier += 1
					break

			# reset the bucket after falling one block
			if max_drop > 0:
				input_bucket = input_bucket_max(player_score)

