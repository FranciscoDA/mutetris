#! /usr/bin/env python3

import sys
import time
import random
import curses
import curses.ascii
from math import floor
from enum import Enum
from copy import copy

palette = [curses.COLOR_WHITE, curses.COLOR_BLACK, 10, 220, 12, 13, 14, 9, 202]
class Colors(Enum):
	white = 0
	black = 1
	green = 2
	yellow = 3
	blue = 4
	purple = 5
	cyan = 6
	red = 7
	orange = 8

def mkcol(fg, bg):
	if fg is not None and bg is not None:
		return curses.color_pair(fg.value * len(palette) + bg.value + 1)
	return 0

block_w = 2
block_h = 1
def draw_block(stdscr, x, y, bgcol, s='()', fg=[Colors.white, Colors.black]):
	try:
		for xpos, (ch, fgcol) in enumerate(zip(s, fg), start=x):
			stdscr.addstr(y, xpos, ch, mkcol(fgcol, bgcol))
	except:
		pass

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


	def draw(self, stdscr, off_x, off_y):
		for x, y, bg in self:
			if bg is not None:
				draw_block(stdscr, x*block_w+off_x, y*block_h+off_y, bg)
	def draw_message(self, stdscr, off_x, off_y, lines):
		for y,l in enumerate(lines):
			try:
				stdscr.addstr((self.h*block_h - len(lines)) // 2+y, (self.w*block_w-len(l)) // 2, l)
			except:
				pass

	def __iter__(self):
		for y in range(self.h):
			for x in range(self.w):
				yield x, y, self.data[y*self.w+x]

class PieceType:
	def __init__(self, w, h, cx, cy, col, data):
		self.w, self.h, self.cx, self.cy = w, h, cx, cy
		self.col, self.data = col, data
	def __iter__(self):
		for y in range(self.h):
			for x in range(self.w):
				if self.data[y*self.w+x]:
					yield x, y
class Piece:
	def __init__(self, piece_type, x, y, r):
		self.piece_type, self.x, self.y, self.r = piece_type, x, y, r
	def __iter__(self):
		rotmat = [[1, 0, 0, 1], [0, -1, 1, 0], [-1, 0, 0, -1], [0, 1, -1, 0]][self.r]
		for x, y in self.piece_type:
			x -= self.piece_type.cx
			y -= self.piece_type.cy
			yield floor(self.x+x*rotmat[0]+y*rotmat[1]), floor(self.y+x*rotmat[2]+y*rotmat[3])

pieces = [
	PieceType(1, 4, 0.5, 1.5, Colors.red, [
		True,
		True,
		True,
		True
	]),
	PieceType(2, 3, 1, 1, Colors.purple, [
		True, True,
		False, True,
		False, True
	]),
	PieceType(2, 3, 0, 1, Colors.yellow, [
		True, True,
		True, False,
		True, False
	]),
	PieceType(2, 2, .5, .5, Colors.blue, [
		True, True,
		True, True
	]),
	PieceType(3, 2, 1, 1, Colors.green, [
		False, True, False,
		True, True, True
	]),
	PieceType(3, 2, 1, 1, Colors.cyan, [
		False, True, True,
		True, True, False
	]),
	PieceType(3, 2, 1, 1, Colors.orange, [
		True, True, False,
		False, True, True
	]),
]

def canplace(board, piece_type, x, y, r):
	return all(
		0 <= px < board.w and py < board.h and board.get(px, py) is None
		for px, py in Piece(piece_type, x, y, r)
	)
def canmove(board, piece, new_piece_type=None, xoff=0, yoff=0, roff=0):
	return canplace(board, new_piece_type or piece.piece_type, piece.x+xoff, piece.y+yoff, (piece.r+roff)%4)

# decrease the input timer multiplicatively for every 100 points
input_bucket_max = lambda player_score: 0.9 ** (player_score // 100)

class Controls:
	SOFTDROP = curses.KEY_DOWN
	LEFT = curses.KEY_LEFT
	RIGHT = curses.KEY_RIGHT
	ROTATE = curses.KEY_UP
	HARDDROP = curses.ascii.SP
	EXIT = curses.ascii.ESC
	PAUSE = ord('p')
key2str = lambda k: curses.ascii.controlnames[k] if k < len(curses.ascii.controlnames) else chr(k).capitalize()

class Game:
	def __init__(self):
		self.exit = False
		self.board = Board(10, 20)
		self.player_score = 0
		self.piece_counter = 1
		self.piece_current = self.new_piece(random.choice(pieces))
		self.piece_shadow = copy(self.piece_current)
		self.drop_piece(self.piece_shadow)
		self.piece_next = [random.choice(pieces), random.choice(pieces), random.choice(pieces)]
		self.input_bucket = 0

	def debug_rotation_system_loop(self, stdscr):
		self.piece_current.x = self.board.w // 2
		self.piece_current.y = self.board.h // 2
		self.piece_shadow = self.cast_shadow(self.piece_current)
		self.draw(stdscr)
		# draw centroid
		draw_block(stdscr, self.piece_current.x*block_w, self.piece_current.y*block_h, s='[]', fg=[Colors.white, Colors.white], bgcol=None)
		inp = stdscr.getch()
		if inp == Controls.EXIT:
			self.exit = True
		elif inp == Controls.SOFTDROP:
			self.piece_current.piece_type = pieces[(pieces.index(self.piece_current.piece_type)+1)%len(pieces)]
		elif inp == Controls.ROTATE:
			self.piece_current.piece_type = pieces[(pieces.index(self.piece_current.piece_type)-1)%len(pieces)]
		elif inp == Controls.LEFT:
			self.piece_current.r = (self.piece_current.r-1)%4
		elif inp == Controls.RIGHT:
			self.piece_current.r = (self.piece_current.r+1)%4
		elif inp == Controls.HARDDROP:
			self.piece_current.r = 0

	def loop(self, stdscr):
		self.draw(stdscr)
		t = time.time()
		stdscr.timeout(max(0, int((self.input_bucket_max()-self.input_bucket)*1000)))
		inp = stdscr.getch()
		# add the elapsed time to the bucket
		self.input_bucket += time.time() - t
		if inp == Controls.EXIT:
			self.exit = True
		elif inp == Controls.PAUSE:
			self.pause_screen(stdscr)
		elif inp == Controls.LEFT and canmove(self.board, self.piece_current, xoff=-1):
			self.piece_current.x -= 1
			self.piece_shadow = self.cast_shadow(self.piece_current)
		elif inp == Controls.RIGHT and canmove(self.board, self.piece_current, xoff=+1):
			self.piece_current.x += 1
			self.piece_shadow = self.cast_shadow(self.piece_current)
		elif inp == Controls.ROTATE:
			for x in [0, -1, +1]:
				if canmove(self.board, self.piece_current, xoff=x, roff=1):
					self.piece_current.r = (self.piece_current.r+1) % 4
					self.piece_current.x += x
					self.piece_shadow = self.cast_shadow(self.piece_current)
					break
		else:
			max_drop = 0
			if inp == Controls.SOFTDROP or inp == -1:
				max_drop = 1
			elif inp == Controls.HARDDROP:
				max_drop = -1
			if not self.drop_piece(self.piece_current, max_drop):
				for px, py in self.piece_current:
					if py < 0:
						self.game_over_screen(stdscr)
						self.exit = True
						break
					self.board.set(px, py, self.piece_current.piece_type.col)

				multiplier = 1
				# check for a complete row and clear it
				for y in range(self.board.h):
					if all(self.board.get(x,y) is not None for x in range(self.board.w)):
						self.board.clear(y)
						self.player_score += self.board.w * multiplier
						multiplier += 1

				self.piece_current = self.new_piece(self.piece_next[0])
				self.piece_shadow = self.cast_shadow(self.piece_current)
				self.piece_next[0:-1] = self.piece_next[1:]
				self.piece_next[-1] = random.choice(pieces)
				self.piece_counter += 1
				if self.piece_counter % 8 == 0:
					random.seed(time.time())

			# reset the bucket after falling one block
			if max_drop > 0:
				self.input_bucket = 0

	def pause_screen(self, stdscr):
		self.board.draw_message(stdscr, 0, 0, ['Paused', key2str(Controls.PAUSE) + ' to unpause'])
		stdscr.timeout(-1)
		while stdscr.getch() != Controls.PAUSE:
			pass
	def game_over_screen(self, stdscr):
		self.board.draw_message(stdscr, 0, 0, ['Game Over', key2str(Controls.EXIT) + ' to quit'])
		stdscr.timeout(-1)
		while stdscr.getch() != Controls.EXIT:
			pass

	def draw(self, stdscr):
		stdscr.erase()
		self.board.draw(stdscr, 0, 0)
		for x, y in self.piece_shadow:
			draw_block(stdscr, x*block_w, y*block_h, None)
		for x, y in self.piece_current:
			draw_block(stdscr, x*block_w, y*block_h, self.piece_current.piece_type.col)
		stdscr.vline(0, self.board.w*block_w, '|', self.board.h*block_h)
		stdscr.hline(self.board.h*block_h, 0, '-', self.board.w*block_w)

		stdscr.addstr(0, self.board.w*block_w+2, 'Next:')
		stdscr.hline(1, self.board.w*block_w+1, '-', 4*block_w)
		for i,n in enumerate(self.piece_next):
			for x, y in n:
				draw_block(stdscr, self.board.w * block_w + 2 + x * block_w, 2 + y * block_h + i * 5 * block_h, n.col)
			stdscr.hline(2+i*5*block_h+4, self.board.w*block_w+1, '-', 4*block_w)
		stdscr.vline(0, self.board.w*block_w+1+4*block_w, '|', len(self.piece_next)*5*block_h+1)

		msglen = len('Score: 0000')
		stdscr.addstr(self.board.h * block_h + 1, self.board.w // 2 * block_w - msglen//2, 'Score: ' + str(self.player_score))
		stdscr.hline(self.board.h*block_h+2, 0, '-', self.board.w*block_w)
		stdscr.vline(self.board.h*block_h+1, self.board.w*block_w, '|', 1)


	def new_piece(self, piece_type):
		return Piece(piece_type, self.board.w//2, 0, 0)

	def drop_piece(self, piece, max_drop=-1): # true if not dropped to bottom
		while max_drop != 0:
			if canmove(self.board, piece, yoff=+1):
				piece.y += 1
				max_drop -= 1
			else:
				return False
		return True
	def cast_shadow(self, piece):
		s = copy(piece)
		self.drop_piece(s)
		return s

	def input_bucket_max(self):
		return input_bucket_max(self.player_score if self.piece_current.y < self.piece_shadow.y else 0)

def main(stdscr, debug=False):
	random.seed(time.time())
	curses.start_color()
	curses.use_default_colors()
	for fg in Colors:
		for bg in Colors:
			curses.init_pair(fg.value*len(palette)+bg.value+1, palette[fg.value], palette[bg.value])
	curses.curs_set(0)
	g = Game()
	while not g.exit:
		if not debug:
			g.loop(stdscr)
		else:
			g.debug_rotation_system_loop(stdscr)
	return g.player_score

if __name__ == '__main__':
	if len(sys.argv)==1:
		player_score = curses.wrapper(main)
		print('Game Over')
		print('Final score: ' + str(player_score))
	elif len(sys.argv)==2 and sys.argv[1] == 'debug':
		curses.wrapper(main, True)

