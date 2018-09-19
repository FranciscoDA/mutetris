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

class Board:
	def __init__(self, w, h):
		self.w, self.h = w, h
		self.data = [None for _ in range(w*h)]
	def in_bounds(self, x, y): return 0 <= x < self.w and 0 <= y < self.h
	def get(self, x, y):
		return self.data[y*self.w+x] if self.in_bounds(x,y) else None
	def set(self, x, y, v):
		if self.in_bounds(x, y):
			self.data[y*self.w+x] = v
		else:
			raise IndexError()
	def clear(self, y):
		self.data[self.w:(y+1)*self.w] = self.data[0:y*self.w]
		self.data[0:self.w] = [None] * self.w

pieces = [ # all piece types are defined as a square map of objects
	[
		Col.red,
		Col.red,
		Col.red,
		Col.red,
	],
	[
		Col.ylw, Col.ylw,
		Col.ylw, None,
		Col.ylw, None,
	],
	[
		Col.pur, Col.pur,
		None,    Col.pur,
		None,    Col.pur,
	],
	[
		Col.blu, Col.blu,
		Col.blu, Col.blu,
	],
	[
		None,    Col.grn, None,
		Col.grn, Col.grn, Col.grn,
	],
	[
		None,    Col.cyn, Col.cyn,
		Col.cyn, Col.cyn, None,
	],
	[
		Col.org, Col.org, None,
		None,    Col.org, Col.org,
	],
]
piece_size = [(4, 1), (3, 2), (3, 2), (2,2), (2,3), (2,3), (2, 3)]

def draw(board, piece_type, piece_x, piece_y, piece_r, piece_next, player_score):
	buf = ANSI_cursor_position(1,1)
	block_width = 2
	active_block = '\033[38;5;7m[\033[38;5;0m]'
	inactive_block = active_block
	blank = '  '
	shadow = '[]'
	shadow_x, shadow_y = piece_x, piece_y
	while canmove(board, piece_type, shadow_x, shadow_y+1, piece_r):
		shadow_y += 1

	# draw the main area
	for y in range(board.h):
		for x in range(board.w):
			ch = board.get(x, y)
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
	buf += ANSI_cursor_position(2, (board.w+1)*block_width+1) + 'Next:'
	for py in range(5):
		buf += ANSI_cursor_position(3+py, (board.w+1) * block_width + 1)
		for px in range(5):
			ch = getpieceblock(piece_next, px, py, 0)
			if ch is not None:
				buf += ch.value + active_block + ANSI_reset
			else:
				buf += blank

	# draw the score
	buf += ANSI_cursor_position(12, (board.w+1)*block_width+1)
	buf += 'Score: ' + str(player_score)
	buf += ANSI_cursor_position(board.h+1, 1)

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
			x = sys.stdin.buffer.read1(-1)
			return x
		return None
	finally:
		termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, oldattrs)

def canmove(board, piece_type, piece_x, piece_y, piece_r):
	return all(
		pblk is None or 0 <= px+piece_x < board.w and py+piece_y < board.h and board.get(px+piece_x, py+piece_y) is None
		for px, py, pblk in iterpieceblocks(piece_type, piece_r)
	)

def getpieceblock(piece_type, px, py, piece_r):
	# get a block inside a (possibly rotated) piece from
	# the px,py coordinates, which are relative to the top-left of the piece
	piece_h, piece_w = piece_size[piece_type]
	if piece_r%2 == 1: px, py = py, px
	if 1 <= piece_r <= 2: py = piece_h-1-py
	if 2 <= piece_r <= 3: px = piece_w-1-px

	if px < 0 or px >= piece_w or py < 0 or py >= piece_h:
		return None
	else:
		return pieces[piece_type][py*piece_w+px]

def iterpieceblocks(piece_type, piece_r):
	# iterate all the sub blocks of a piece
	piece_h, piece_w = piece_size[piece_type]
	if piece_r%2 == 1: piece_h, piece_w = piece_w, piece_h
	return (
		(px, py, getpieceblock(piece_type, px, py, piece_r)) for py in range(piece_h) for px in range(piece_w)
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
	board = Board(10, 20)
	exit = False

	player_score = 0
	piece_counter = 1
	piece_type = random.randrange(len(pieces))
	piece_h, piece_w = piece_size[piece_type]
	piece_x, piece_y, piece_r = board.w//2 - piece_w//2, 1-piece_h, 0
	piece_next = random.randrange(len(pieces))

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
				max_drop = board.h + piece_h
			for _ in range(max_drop):
				if canmove(board, piece_type, piece_x, piece_y + 1, piece_r):
					piece_y += 1
				else:
					for px, py, pblk in iterpieceblocks(piece_type, piece_r):
						if pblk is not None:
							if py+piece_y < 0:
								exit = True # game over
								break
							board.set(px+piece_x, py+piece_y, pblk)
					piece_type = piece_next
					piece_h, piece_w = piece_size[piece_type]
					piece_x, piece_y, piece_r = board.w//2 - piece_w//2, 1-piece_h, 0
					piece_next = random.randrange(len(pieces))
					piece_counter += 1
					if piece_counter % 5 == 0:
						random.seed(time.time())
					multiplier = 1
					# check for a complete row and clear it
					for y in range(board.h):
						if all(board.get(x,y) is not None for x in range(board.w)):
							board.clear(y)
							player_score += board.w * multiplier
							multiplier += 1
					break

			# reset the bucket after falling one block
			if max_drop > 0:
				input_bucket = input_bucket_max(player_score)

