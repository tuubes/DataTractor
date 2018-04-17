#!/usr/bin/python3

from os import getcwd, makedirs, path
from sys import argv, exit
from getopt import *
from datatractor.main.packets_extractor import *
from datatractor.main.scala_generator import *
import shutil

# Main program
try:
	opts, args = getopt(argv[1:], "v:o:")
except GetoptError:
	print("Usage: xtract.py -v <game_version> [-o <output_dir>]")
	exit(2)
else:
	game_version = None
	output_dir = None
	for opt, arg in opts:
		if opt == "-v":
			game_version = arg
		elif opt == "-o":
			output_dir = arg

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

	protocol = extract_packets(game_version)

	print("Generating Scala files...")
	sub: SubProtocol
	for sub in [protocol.handshake, protocol.status, protocol.login, protocol.play]:
		sub_name = sub.name.lower()
		print("Processing %s packets..." % sub_name)
		dir_cb = "%s/%s/clientbound" % (output_dir, sub_name)
		dir_sb = "%s/%s/serverbound" % (output_dir, sub_name)
		makedirs(dir_cb)
		makedirs(dir_sb)
		for packet in sub.clientbound:
			write_packet_class(dir_cb, packet)
		for packet in sub.serverbound:
			write_packet_class(dir_sb, packet)

	print("Generation complete!")