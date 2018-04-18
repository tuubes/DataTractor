#!/usr/bin/python3

import os
import sys
import shutil
import requests_cache

from getopt import getopt, GetoptError
from datatractor.main.extractors import PacketsExtractor, BlocksExtractor

# Main program
usage = "xtract.py -v <game_version> [-o <output_dir>] [--nocache | --cachetime <cache_timeout>]"

try:
	opts, args = getopt(sys.argv[1:], "v:o:pb", ["packets, blocks, help, nocache, cachetime="])
except GetoptError:
	print("Usage:", usage)
	exit(2)
else:
	# Extractors
	extractors = []
	# Misc params
	game_version = None
	output_dir = None
	use_cache = True
	cache_timeout = 300
	for opt, arg in opts:
		if opt == "--help":
			print("xtract.py - Data extractor for Tuubes (http://tuubes.org)")
			print("Usage:", usage)
			exit(0)
		elif opt == "-v":
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
		output_dir = "%s/out/generated_%s" % (os.getcwd(), game_version)
	if output_dir.endswith("/"):
		output_dir = output_dir[:-1]

	print("Using output dir %s" % output_dir)
	if os.path.isdir(output_dir):
		shutil.rmtree(output_dir, ignore_errors=True)
		print("Output dir cleaned")

	if use_cache:
		print("Using requests_cache with a timeout of %s seconds" % cache_timeout)
		requests_cache.install_cache("out/http_cache", "sqlite", cache_timeout)

	for opt, arg in opts:
		if opt == "p" or opt == "packets":
			extractors.append(PacketsExtractor(game_version))
		elif opt == "b" or opt == "blocks":
			extractors.append(BlocksExtractor(game_version))

	if len(extractors) == 0:
		print("No extractors specified, let's run all of them!")
		extractors = [PacketsExtractor(game_version), BlocksExtractor(game_version)]

	for extractor in extractors:
		print("====", extractor.name, "====")
		extractor.extract(output_dir)
		print("============================\n")
	print("Done!")
