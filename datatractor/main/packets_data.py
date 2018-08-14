from utils.string_tools import *


class Field:
	"""A field"""

	def __init__(self, name, type, comment):
		# DEBUG print("Field: %s:%s, %s:%s, %s;%s" % (name_str, type(name_str), type_str, type(type_str), comment, type(comment)))
		self.name = to_camel_case(to_snake_varname(name))
		self.type = type
		self.comment = comment

	def __repr__(self):
		return "Field(%s: %s // %s)" % (self.name, self.type, self.comment)

	def __str__(self):
		return "Field(%s: %s)" % (self.name, self.type)


class Compound:
	"""A field composed of other fields"""

	def __init__(self, name):
		self.name = name
		self.entries = []

	def add_field(self, field: Field):
		self.entries.append(field)

	def add_switch(self, switch):
		self.entries.append(switch)


class Switch:
	"""The data changes depending on another field, which should be an enum"""

	def __init__(self, field: Field):
		self.field = field
		field.switch = self
		self.entries = []

	def add_entry(self, value, name, data: Compound):
		self.entries.append((value, name, data))


class Enum:
	"""A field with a limited number of values, usually integers"""

	def __init__(self, field: Field):
		self.field = field
		field.enum = self
		self.entries = []

	def add_entry(self, value, name):
		self.entries.append((value, name))


class Packet:
	"""A packet"""

	def __init__(self, name, id_str, fields):
		self.name = to_pascal_case(to_snake_classname(name))
		self.id = int(id_str, 0)
		self.fields = fields

	def __repr__(self):
		return "Packet(%s, %s, %s)" % (self.name, self.id, repr(self.fields))

	def __str__(self):
		return "Packet(%s, %s, %d fields)" % (self.name, self.id, len(self.fields))


class Protocol:
	"""Full Minecraft protocol"""

	def __init__(self, game_version, number, sub_handshake, sub_play, sub_status, sub_login):
		self.game_version = game_version
		self.number = number
		self.handshake = sub_handshake
		self.play = sub_play
		self.status = sub_status
		self.login = sub_login

	def __repr__(self):
		return "Protocol(%s, %d, handshake:%s, play:%s, status:%s, login:%s)" % (
			self.game_version, self.number, repr(self.handshake), repr(self.play), repr(self.status), repr(self.login))

	def __str__(self):
		return "Protocol(%s, %d, %s, %s, %s, %s)" % (
			self.game_version, self.number, str(self.handshake), str(self.play), str(self.status), str(self.login))


class SubProtocol:
	"""Sub-protocol"""

	def __init__(self, name, packets_cb, packets_sb):
		self.name = name
		self.clientbound = packets_cb
		self.serverbound = packets_sb

	def __repr__(self):
		return "SubProtocol(%s, client_bound:%s, server_bound:%s)" % (self.name, self.clientbound, self.serverbound)

	def __str__(self):
		return "SubProtocol(%s, client_bound:%d packets, server_bound:%d packets)" % (
			self.name, len(self.clientbound), len(self.serverbound))

	def packet_count(self):
		return len(self.clientbound) + len(self.serverbound)

	def clientbound_byname(self, packet_name: str):
		snake = to_snake_case(packet_name)
		for packet in self.clientbound:
			if packet.name_snake == snake:
				return packet
		return None

	def serverbound_byname(self, packet_name: str):
		snake = to_snake_case(packet_name)
		for packet in self.serverbound:
			if packet.name_snake == snake:
				return packet
		return None

	def clientbound_byid(self, packet_id: int):
		return self.clientbound[packet_id]

	def serverbound_byid(self, packet_id: int):
		return self.serverbound[packet_id]
