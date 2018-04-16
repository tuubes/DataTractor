from datatractor.mcpc import packets_extractor

game_version = input("Game Version: ").strip()
protocol = packets_extractor.extract_packets(game_version)
print(repr(protocol))