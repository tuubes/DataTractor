from datatractor.main import packets_extractor, scala_writer

game_version = input("Game Version: ").strip()
protocol = packets_extractor.extract_packets(game_version)
print(repr(protocol))

for packet in protocol.play.clientbound:
	print("====", packet.name, "====")
	for field in packet.fields:
		comment = "" if (field.comment is None) else field.comment
		stype = scala_writer.scala_type(field.type)
		a = "%s : %s" % (field.name, stype)
		aligned = a + " " * (max(0, 30 - len(a)))
		print("%s || %s" % (aligned, comment))
