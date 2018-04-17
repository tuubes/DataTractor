from datatractor.main.blocks_extractor import *
from datatractor.utils.gamepedia_wiki_tools import *

requests_cache.install_cache("out/http_cache", "sqlite", 3000)

version = "1.11"
release_date, next_version, next_date = extract_release_infos(version, True)
print("Version: %s released on %s" % (version, release_date))
print("Next version: %s released on %s" % (next_version, next_date))

blocks = extract_blocks(next_date)
print(blocks)
