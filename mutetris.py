#! /usr/bin/env python3

import time
import random
import curses
import curses.ascii
from enum import Enum

palette = [curses.COLOR_WHITE, curses.COLOR_BLACK, 10, 220, 12, 13, 14, 9, 202]
class Col(Enum):
	wht = 0
	blk = 1
	grn = 2
	ylw = 3
	blu = 4
	pur = 5
	cyn = 6
	red = 7
	org = 8

def mkcol(fg, bg):
	x = curses.color_pair(fg.value * len(palette) + bg.value + 1)
	return x

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

tile_width = 2
tile_height = 1
def draw(stdscr, board, piece_type, piece_x, piece_y, piece_r, piece_next, player_score):
	stdscr.erase()
	active_block = '()'
	active_block_fg = [Col.wht, Col.blk]
	inactive_block = active_block
	inactive_block_fg = active_block_fg
	shadow = '()'
	shadow_fg = active_block_fg
	shadow_x, shadow_y = piece_x, piece_y
	while canmove(board, piece_type, shadow_x, shadow_y+1, piece_r):
		shadow_y += 1

	# draw the main area
	for y in range(board.h):
		for x in range(board.w):
			bg = board.get(x, y)
			if bg is not None:
				for x0, (ch, fg) in enumerate(zip(inactive_block, inactive_block_fg)):
					stdscr.addstr(y*tile_height, x*tile_width+x0, ch, mkcol(fg, bg))
	for x, y, bg in iterpieceblocks(piece_type, piece_r):
		for x0, (ch, fg) in enumerate(zip(shadow, shadow_fg)):
			try:
				stdscr.addch((y+shadow_y)*tile_height, (x+piece_x)*tile_width+x0, ch)
			except:
				pass
		for x0, (ch, fg) in enumerate(zip(active_block, active_block_fg)):
			try:
				stdscr.addstr((y+piece_y)*tile_height, (x+piece_x)*tile_width+x0, ch, mkcol(fg, bg))
			except:
				pass

	stdscr.addstr(3, board.w*tile_width+2, 'Next:')
	for x, y, bg in iterpieceblocks(piece_next, 0):
		for x0, (ch, fg) in enumerate(zip(active_block, active_block_fg)):
			stdscr.addstr(3+y*tile_height+1, (board.w+x)*tile_width+x0+2, ch, mkcol(fg, bg))

	stdscr.addstr(12, board.w*tile_width+2, 'Score: ' + str(player_score))
	stdscr.vline(0, board.w*tile_width, '|', board.h*tile_height)
	stdscr.hline(board.h*tile_height, 0, '-', board.w*tile_width)

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
	for py in range(piece_h):
		for px in range(piece_w):
			blk = getpieceblock(piece_type, px, py, piece_r)
			if blk != None:
				yield (px, py, blk)

# decrease the input timer multiplicatively for every 100 points
input_bucket_max = lambda player_score: 0.85 ** (player_score // 100)

class Controls:
	SOFTDROP = curses.KEY_DOWN
	LEFT = curses.KEY_LEFT
	RIGHT = curses.KEY_RIGHT
	ROTATE = curses.KEY_UP
	HARDDROP = curses.ascii.SP
	EXIT = curses.ascii.ESC
	PAUSE = ord('p')

def draw_message(stdscr, board, msg):
	stdscr.addstr(board.h * tile_height // 2, board.w * tile_width // 2 - len(msg) // 2, msg)

def main(stdscr):
	random.seed(time.time())
	board = Board(10, 20)
	exit = False
	curses.start_color()
	curses.use_default_colors()
	for fg in Col:
		for bg in Col:
			curses.init_pair(fg.value*len(palette)+bg.value+1, palette[fg.value], palette[bg.value])

	player_score = 0
	piece_counter = 1
	piece_type = random.randrange(len(pieces))
	piece_h, piece_w = piece_size[piece_type]
	piece_x, piece_y, piece_r = board.w//2 - piece_w//2, 1-piece_h, 0
	piece_next = random.randrange(len(pieces))

	input_bucket = input_bucket_max(player_score)
	while not exit:
		draw(stdscr, board, piece_type, piece_x, piece_y, piece_r, piece_next, player_score)
		t = time.time()
		stdscr.timeout(max(0, int(input_bucket*1000)))
		inp = stdscr.getch()
		# deduct the elapsed time from the bucket
		input_bucket -= time.time() - t
		if inp == Controls.EXIT:
			exit = True
		elif inp == Controls.PAUSE:
			draw_message(stdscr, board, 'Paused')
			stdscr.timeout(-1)
			while stdscr.getch() != Controls.PAUSE:
				pass
		elif inp == Controls.LEFT and canmove(board, piece_type, piece_x-1, piece_y, piece_r):
			piece_x -= 1
		elif inp == Controls.RIGHT and canmove(board, piece_type, piece_x+1, piece_y, piece_r):
			piece_x += 1
		elif inp == Controls.ROTATE:
			for x in [0, -1, 1]:
				if canmove(board, piece_type, piece_x+x, piece_y, (piece_r+1)%4):
					piece_r = (piece_r+1) % 4
					piece_x += x
					break
		else:
			max_drop = 0
			if inp == Controls.SOFTDROP or inp == -1:
				max_drop = 1
			elif inp == Controls.HARDDROP:
				max_drop = board.h + piece_h
			for _ in range(max_drop):
				if canmove(board, piece_type, piece_x, piece_y + 1, piece_r):
					piece_y += 1
				else:
					for px, py, pblk in iterpieceblocks(piece_type, piece_r):
						if pblk is not None:
							if py+piece_y < 0:
								draw_message(stdscr, board, 'Game Over')
								stdscr.timeout(-1)
								while stdscr.getch() != Controls.EXIT:
									pass
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

if __name__ == '__main__':
	curses.wrapper(main)
