#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  clausiusd.py
#  
#  Copyright 2012 Philip Pum <philippum@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

__author__ = "Philip Pum"
__copyright__ = "Copyright (C) 2012 Philip Pum"
__credits__ = "Scott Williams"
__license__ = "GPL"
__maintainer__ = "Philip Pum"
__email__ = "philippum@gmail.com"
__version__ = "0.1"
__contact__ = "https://github.com/ifoo/clausius"

import argparse

class MatplotlibRenderer(object):
	def __init__(self, data_points, unit, destination):
		self.__datapoints = data_points
		self.__unit = unit
		self.__destination = destination

	def render(self):
		import matplotlib.pyplot as plt

		# TODO: render
		raise NotImplementedError

class GoogleRenderer(object):
	def __init__(self, data_points, unit, destination):
		self.__datapoints = data_points
		self.__unit = unit
		self.__destination = destination

	def render(self):
		# TODO: implement
		raise NotImplementedError

def read_data_points(filename, unit):
	with open(filename, "rb") as file_handle:
		def split_iterator(data, size):
			assert size > 0
			for start in xrange(0, len(data), size):
				yield data[start:start+size]

		def convert_units(schema, val):
			conversion_matrix = { 	"cc": lambda x: x,
									"cf": lambda x: x*1.8 + 32.0,
									"ck": lambda x: x+273.15,
									"fc": lambda x: (x-32.0)/1.8,
									"ff": lambda x: x,
									"fk": lambda x: (x-32.0)/1.8 + 273.15,
									"kc": lambda x: x-273.15,
									"kf": lambda x: (x-273.15)*1.8 + 32.0,
									"kk": lambda x: x}
			return conversion_matrix[schema](val)

		import struct

		data_points = []

		for x in split_iterator(file_handle.read(), 7):
			b1, b2, u, ts = struct.unpack("!BBcf", x)
			print b1, b2
			temp = float(b1) + float(b2) * 0.01
			data_points.append((convert_units("%c%c" % (u, unit), temp), ts))
		return data_points


def main():
	parser = argparse.ArgumentParser(description="Client tool for the clausiusd CPU monitoring daemon", epilog="%s (%s). Visit %s for more information." % (__copyright__, __email__, __contact__))
	parser.add_argument("-f", "--data-file", nargs=1, required=True, help="specify the data file")
	parser.add_argument("-d", "--destination", nargs=1, required=True, help="specify the destination file")
	parser.add_argument("-r", "--renderer", nargs=1, choices=["matplotlib", "google"], default="matplotlib", help="define render engine")
	parser.add_argument("-u", "--unit", nargs=1, choices=["c", "f", "k"], default="c", help="define temperature unit")
	args = parser.parse_args()

	(MatplotlibRenderer if args.renderer == "matplotlib" else GoogleRenderer)(read_data_points(args.data_file[0], args.unit), args.unit, args.destination).render()
	

if __name__ == "__main__":
	main()