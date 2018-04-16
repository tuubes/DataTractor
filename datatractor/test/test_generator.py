from datatractor.main import packets_extractor, scala_generator

game_version = input("Game Version: ").strip()
protocol = packets_extractor.extract_packets(game_version)
print(repr(protocol))

for packet in protocol.play.clientbound:
	pname, pclass = scala_generator.generate_packet_class(packet)
	print("===============", pname, "===============")
	print(pclass)
	print("\n")