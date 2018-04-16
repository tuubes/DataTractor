from datatractor.main import packets_extractor, scala_writer

game_version = input("Game Version: ").strip()
protocol = packets_extractor.extract_packets(game_version)
print(repr(protocol))

for packet in protocol.play.clientbound:
	print("====", packet.name, "====")
	for field in packet.fields:
		print(field.name, ":", scala_writer.scala_type(field.type))