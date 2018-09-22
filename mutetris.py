#! /usr/bin/env python3

import time
import random
import curses
import curses.ascii
from math import floor
from enum import Enum

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
	PieceType(1, 4, 0, 2, Colors.red, [
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
	PieceType(2, 2, 0.5, 0.5, Colors.blue, [
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

def draw(stdscr, board, piece_current, piece_next, player_score):
	stdscr.erase()
	shadow_x, shadow_y = piece_current.x, piece_current.y
	while canplace(board, piece_current.piece_type, shadow_x, shadow_y+1, piece_current.r):
		shadow_y += 1

	# draw the main area
	board.draw(stdscr, 0, 0)
	for x, y in Piece(piece_current.piece_type, shadow_x, shadow_y, piece_current.r):
		draw_block(stdscr, x*block_w, y*block_h, None)
	for x, y in piece_current:
		draw_block(stdscr, x*block_w, y*block_h, piece_current.piece_type.col)

	stdscr.addstr(3, board.w*block_w+2, 'Next:')
	for x, y in piece_next:
		draw_block(stdscr, board.w * block_w + 2 + x * block_w, 4 + y * block_h, piece_next.col)

	stdscr.addstr(12, board.w*block_w+2, 'Score: ' + str(player_score))
	stdscr.vline(0, board.w*block_w, '|', board.h*block_h)
	stdscr.hline(board.h*block_h, 0, '-', board.w*block_w)

def canplace(board, piece_type, x, y, r):
	return all(
		0 <= px < board.w and py < board.h and board.get(px, py) is None
		for px, py in Piece(piece_type, x, y, r)
	)

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

def main(stdscr):
	random.seed(time.time())
	board = Board(10, 20)
	exit = False
	curses.start_color()
	curses.use_default_colors()
	for fg in Colors:
		for bg in Colors:
			curses.init_pair(fg.value*len(palette)+bg.value+1, palette[fg.value], palette[bg.value])
	curses.curs_set(0)

	player_score = 0
	piece_counter = 1

	piece_current = Piece(random.choice(pieces), board.w//2, 1, 0)
	piece_current.x -= piece_current.piece_type.w//2
	piece_current.y -= piece_current.piece_type.h
	piece_next = random.choice(pieces)

	input_bucket = input_bucket_max(player_score)
	while not exit:
		draw(stdscr, board, piece_current, piece_next, player_score)
		t = time.time()
		stdscr.timeout(max(0, int(input_bucket*1000)))
		inp = stdscr.getch()
		# deduct the elapsed time from the bucket
		input_bucket -= time.time() - t
		if inp == Controls.EXIT:
			exit = True
		elif inp == Controls.PAUSE:
			board.draw_message(stdscr, 0, 0, ['Paused', 'P to unpause'])
			stdscr.timeout(-1)
			while stdscr.getch() != Controls.PAUSE:
				pass
		elif inp == Controls.LEFT and canplace(board, piece_current.piece_type, piece_current.x-1, piece_current.y, piece_current.r):
			piece_current.x -= 1
		elif inp == Controls.RIGHT and canplace(board, piece_current.piece_type, piece_current.x+1, piece_current.y, piece_current.r):
			piece_current.x += 1
		elif inp == Controls.ROTATE:
			for x in [0, -1, +1]:
				if canplace(board, piece_current.piece_type, piece_current.x+x, piece_current.y, (piece_current.r+1)%4):
					piece_current.r = (piece_current.r+1) % 4
					piece_current.x += x
					break
		else:
			max_drop = 0
			if inp == Controls.SOFTDROP or inp == -1:
				max_drop = 1
			elif inp == Controls.HARDDROP:
				max_drop = board.h + piece_current.piece_type.h
			for _ in range(max_drop):
				if canplace(board, piece_current.piece_type, piece_current.x, piece_current.y + 1, piece_current.r):
					piece_current.y += 1
				else:
					for px, py in piece_current:
						if py < 0:
							board.draw_message(stdscr, 0, 0, ['Game Over', 'Esc to quit'])
							stdscr.timeout(-1)
							while stdscr.getch() != Controls.EXIT:
								pass
							exit = True # game over
							break
						board.set(px, py, piece_current.piece_type.col)
					piece_current = Piece(piece_next, board.w//2 - piece_next.w//2, 1-piece_next.h, 0)
					piece_next = random.choice(pieces)
					piece_counter += 1
					if piece_counter % 8 == 0:
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
