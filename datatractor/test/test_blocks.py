from datatractor.main.blocks_extractor import *
from datatractor.utils.gamepedia_wiki_tools import *

requests_cache.install_cache("out/http_cache", "sqlite", 300)

version = "1.11"
release_date, next_version, next_date = extract_release_infos(version, True)
print("Version: %s released on %s" % (version, release_date))
print("Next version: %s released on %s" % (next_version, next_date))

blocks_url = get_revision_url("Java_Edition_data_values/Block_IDs", next_date)
blocks_url = blocks_url + "&modules=noscript&only=styles&skin=hydra"
print("Block IDs for version %s: %s" % (version, blocks_url))

blocks = extract_blocks(blocks_url)
print(blocks)
