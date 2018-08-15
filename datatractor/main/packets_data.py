from typing import Tuple, Any, Dict, Set, List

from utils.html_tools import *
from utils.string_tools import *


class Field:
	"""A field"""

	def __init__(self, name: str, type: str, comment: str):
		# DEBUG print("Field: %s:%s, %s:%s, %s;%s" % (name_str, type(name_str), type_str, type(type_str), comment, type(comment)))
		self.name = name
		self.type = type
		self.comment = comment

	def __repr__(self):
		return "Field(%s: %s // %s)" % (self.name, self.type, self.comment)

	def __str__(self):
		return "Field(%s: %s)" % (self.name, self.type)


class Compound:
	"""A structure composed of fields"""

	def __init__(self, name, field=None):
		self.name = name
		self.entries = []
		if field is not None:
			field.compound = self

	def add_field(self, field: Field):
		self.entries.append(field)

	def add_switch(self, switch):
		self.entries.append(switch)

	def is_empty(self):
		return len(self.entries) == 0


class SwitchEntry(Compound):
	"""Switch entry"""

	def __init__(self, value, name):
		super().__init__(name)
		self.value = value


class Switch:
	"""The data changes depending on another field, which should be an enum"""
	entries: List[SwitchEntry]

	def __init__(self, field: Field):
		self.field = field
		field.switch = self
		self.entries = []
		self.name = field.name.title()

	def add_entry(self, entry: SwitchEntry):
		self.entries.append(entry)


class EnumEntry:
	def __init__(self, value, name, comments=None):
		self.value = value
		self.name = name
		self.comments = comments

class Enum:
	"""A field with a limited number of values, usually integers"""
	entries: List[EnumEntry]

	def __init__(self, field: Field):
		self.field = field
		field.enum = self
		self.entries = []
		self.name = field.name.title()

	def add_entry(self, entry: EnumEntry):
		self.entries.append(entry)


class Packet:
	"""A packet"""

	def __init__(self, name: str, id: int, fields):
		self.name = name
		self.id = id
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
		snake = snake_case(packet_name)
		for packet in self.clientbound:
			if packet.name_snake == snake:
				return packet
		return None

	def serverbound_byname(self, packet_name: str):
		snake = snake_case(packet_name)
		for packet in self.serverbound:
			if packet.name_snake == snake:
				return packet
		return None

	def clientbound_byid(self, packet_id: int):
		return self.clientbound[packet_id]

	def serverbound_byid(self, packet_id: int):
		return self.serverbound[packet_id]


class PacketContext:
	"""
	Stores data during the packet construction
	"""
	tables_data: List[Tuple[Any, HtmlTable]]
	main_above: object
	main_table: HtmlTable
	dict_fields: Dict[str, Field]
	dict_switches: Dict[str, Switch]
	dict_compounds: Dict[str, Compound]
	dict_enums: Dict[str, Enum]
	set_used_types: Set[str]

	def __init__(self, tables_with_above_elements: List[Tuple[Any, HtmlTable]]):
		self.tables_data = tables_with_above_elements
		self.main_above = tables_with_above_elements[0][0]
		self.main_table = tables_with_above_elements[0][1]
		self.dict_fields = {}
		self.dict_switches = {}
		self.dict_compounds = {}
		self.dict_enums = {}
		self.set_used_types = {}

	def register_field(self, field):
		self.dict_fields[field.name] = field
		self.register_used_type(field.type)

	def register_switch(self, switch):
		self.dict_switches[switch.name] = switch

	def register_compound(self, compound):
		self.dict_compounds[compound.name] = compound

	def register_enum(self, enum):
		self.dict_enums[enum.name] = enum

	def register_used_type(self, type: str):
		if '[' in type:
			type = type[:type.index('[')]
		self.set_used_types.add(type)


class LocalContext:
	"""
	Stores local data during the packet construction
	"""
	rowlimit: int
	above_table: object
	table: List[List[HtmlCell]]

	def __init__(self, table_with_above: Tuple[Any, HtmlTable]):
		self.above_table = table_with_above[0]
		self.table = table_with_above[1].rows
		self.rowlimit = len(self.table)

		# Detect the field_names, field_types and field_notes columns
		first_row = self.table[0]
		ncol = len(first_row)
		i = 0
		while i < ncol:
			cell = first_row[i]
			i += 1
			if not isinstance(cell, RefCell):
				text = get_text(cell).strip().lower()
				if text == "field name":
					self.names_col = i
				elif text == "field type":
					self.types_col = i
				elif text == "notes":
					self.notes_col = i
		# Standard detection didn't work, assign some default values
		if self.names_col is None:
			self.names_col = 0
		if self.types_col is None:
			self.types_col = 1
		if self.notes_col is None:
			self.notes_col = ncol - 1
