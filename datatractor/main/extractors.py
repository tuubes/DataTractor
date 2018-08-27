import os

import datatractor.main.blocks_extractor as b_extractor
import datatractor.main.packets_extractor as p_extractor
import datatractor.main.scala_generator as generator

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
		generator.init(self.game_version)
		sub: p_extractor.SubProtocol
		for sub in [protocol.handshake, protocol.status, protocol.login, protocol.play]:
			sub_name = sub.name.lower()
			print(f"Processing {sub_name} packets...")
			sub_dir = f"{output_dir}/packets/{sub_name}"

			sub_clientbound = f"{sub_dir}/clientbound"
			os.makedirs(sub_clientbound)
			for packet in sub.clientbound:
				packet: p_extractor.PacketInfos
				if not packet.name().endswith("Packet"):
					packet.main_compound.name += "Packet"
				file = f"{sub_clientbound}/{packet.name()}.scala"
				generator.write_packet_class(packet, file,
											 subpackage=f"packets.{sub_name}.clientbound",
											 infos=f"clientbound, protocol {protocol.number} for MC {protocol.game_version}")

			sub_serverbound = f"{sub_dir}/serverbound"
			os.makedirs(sub_serverbound)
			for packet in sub.serverbound:
				packet: p_extractor.PacketInfos
				if not packet.name().endswith("Packet"):
					packet.main_compound.name += "Packet"
				file = f"{sub_serverbound}/{packet.name()}.scala"
				generator.write_packet_class(packet, file,
											 subpackage=f"packets.{sub_name}.serverbound",
											 infos=f"serverbound, protocol {protocol.number} for MC {protocol.game_version}")

			file = f"{sub_dir}/{sub.name.title()}.scala"
			generator.write_protocol_class(sub, file, importsubpackage=f"packets.{sub_name}.serverbound", subpackage=f"packets.{sub_name}")

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
