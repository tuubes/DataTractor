import requests_cache

from datatractor.utils.gamepedia_wiki_tools import *

requests_cache.install_cache("out/http_cache", "sqlite", 300)

version = "1.11"
release_date, next_version, next_date = extract_release_infos(version, True)
print("Version: %s released on %s" % (version, release_date))
print("Next version: %s released on %s" % (next_version, next_date))

blocks_url = get_revision_url("Java_Edition_data_values/Block_IDs", next_date)
print("Block IDs for version %s: %s" % (version, blocks_url))

items_url = get_revision_url("Java_Edition_data_values/Item_IDs", next_date)
print("Item IDs for version %s: %s" % (version, items_url))

entities_url = get_revision_url("Java_Edition_data_values/Entity_IDs", next_date)
print("Entity IDs for version %s: %s" % (version, entities_url))

stone_url = get_revision_url("Furnace", next_date)
print("Furnace for version %s: %s" % (version, stone_url))