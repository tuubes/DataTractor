#!/usr/bin/python3

import shutil
import sys
from getopt import getopt, GetoptError
from os import getcwd, makedirs, path

import requests_cache

from datatractor.main.packets_extractor import *
from datatractor.main.scala_generator import *

# Main program
usage = "xtract.py -v <game_version> [-o <output_dir>] [--nocache | --cachetime <cache_timeout>]"

try:
	opts, args = getopt(sys.argv[1:], "v:o:", ["help, nocache, cachetime="])
except GetoptError:
	print("Usage:", usage)
	exit(2)
else:
	game_version = None
	output_dir = None
	use_cache = True
	cache_timeout = 300
	for opt, arg in opts:
		if opt == "--help":
			print("xtract.py - Data extractor for Tuubes (http://tuubes.org)")
			print("Usage:", usage)
			exit(0)
		if opt == "-v":
			game_version = arg
		elif opt == "-o":
			output_dir = arg
		elif opt == "--nocache":
			use_cache = False
		elif opt == "--cachetime":
			cache_timeout = int(arg)

	if not game_version:
		print("Missing parameter: -v <game_version>")
		game_version = input("Please enter a version: ")
	if not output_dir:
		output_dir = "%s/out/generated_%s" % (getcwd(), game_version)
	if output_dir.endswith("/"):
		output_dir = output_dir[:-1]

	print("Using output dir %s" % output_dir)
	if path.isdir(output_dir):
		shutil.rmtree(output_dir, ignore_errors=True)
		print("Output dir cleaned")

	if use_cache:
		print("Using requests_cache with a timeout of %s seconds" % cache_timeout)
		requests_cache.install_cache("out/http_cache", "sqlite", cache_timeout)

	protocol = extract_packets(game_version)

	print("Generating Scala files...")
	sub: SubProtocol
	for sub in [protocol.handshake, protocol.status, protocol.login, protocol.play]:
		sub_name = sub.name.lower()
		print("Processing %s packets..." % sub_name)
		dir_cb = "%s/packets/%s/clientbound" % (output_dir, sub_name)
		dir_sb = "%s/packets/%s/serverbound" % (output_dir, sub_name)
		makedirs(dir_cb)
		makedirs(dir_sb)
		for packet in sub.clientbound:
			write_packet_class(dir_cb, packet)
		for packet in sub.serverbound:
			write_packet_class(dir_sb, packet)

	print("Generation complete!")