import datatractor.main.packets_extractor as p_extractor
import datatractor.main.blocks_extractor as b_extractor
import datatractor.main.scala_generator as generator
import os

release_version = None


def get_release_infos(game_version: str):
	global release_version, release_date, next_version, next_date
	if release_version == game_version:
		return release_date, next_version, next_date
	else:
		version = ".".join(game_version.split(".")[:2])
		release_date, next_version, next_date = b_extractor.extract_release_infos(version, True)
		print("Selected version: %s released on %s" % (version, release_date))
		if next_version is None:
			print("Next version: none")
			print("Today's date: %s" % next_date)
		else:
			print("Next version: %s released on %s" % (next_version, next_date))
		release_version = game_version
		return release_date, next_version, next_date


class PacketsExtractor:
	def __init__(self, game_version: str):
		self.name = "Packets Extractor"
		self.game_version = game_version

	def extract(self, output_dir):
		protocol = p_extractor.extract_packets(self.game_version)
		print("Generating Scala files...")
		sub: p_extractor.SubProtocol
		for sub in [protocol.handshake, protocol.status, protocol.login, protocol.play]:
			sub_name = sub.name.lower()
			print("Processing %s packets..." % sub_name)
			dir_cb = "%s/packets/%s/clientbound" % (output_dir, sub_name)
			dir_sb = "%s/packets/%s/serverbound" % (output_dir, sub_name)
			os.makedirs(dir_cb)
			os.makedirs(dir_sb)
			for packet in sub.clientbound:
				generator.write_packet_class(dir_cb, packet)
			for packet in sub.serverbound:
				generator.write_packet_class(dir_sb, packet)

		print("Generation complete!")


class BlocksExtractor:
	def __init__(self, game_version: str):
		self.name = "Blocks Extractor"
		self.game_version = game_version
		a, b, self.next_date = get_release_infos(game_version)

	def extract(self, output_dir):
		blocks = b_extractor.extract_blocks(self.next_date)
		f = open("%s/blocks_full_ids.json" % output_dir, "w")
		f2 = open("%s/blocks_classic_ids.json" % output_dir, "w")
		for block in blocks:
			for json in b_extractor.json_block_variants(block):
				f.write(json)
				f.write("\n")
			json2 = b_extractor.jsonify(block)
			f2.write(json2)
			f2.write("\n")
		f.close()
		f2.close()
