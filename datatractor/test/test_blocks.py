from datatractor.main.blocks_extractor import *
from datatractor.utils.gamepedia_wiki_tools import *

requests_cache.install_cache("out/http_cache", "sqlite", 3000)

version = "1.11"
release_date, next_version, next_date = extract_release_infos(version, True)
print("Version: %s released on %s" % (version, release_date))
print("Next version: %s released on %s" % (next_version, next_date))

blocks = extract_blocks(next_date)
for block in blocks:
	print("====", block.nice_name, "====")
	print("id:", block.numeric_id, block.string_id)
	print("data values:", block.values)
	print("")
	print("flammable:", block.is_flammable)
	print("transparent:", block.is_transparent)
	print("renewable:", block.is_renewable)
	print("")
	print("luminance:", block.luminance)
	print("hardness:", block.hardness)
	print("blast_resistance:", block.blast_resistance)
	print("")
	print("tool:", block.tool)
	print("max_stack:", block.max_stack)
