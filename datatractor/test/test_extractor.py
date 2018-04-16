from datatractor.mcpc import packets_extractor

packets_extractor.extract_packets("1.10.2")
protocol = packets_extractor.extract_packets("1.12.2")
print(repr(protocol))