from typing import Any, Dict

from utils.html_tools import *
from utils.string_tools import *


class Field:
	"""A field"""

	def __init__(self, name: str, type: str, comment: str):
		# DEBUG print("Field: %s:%s, %s:%s, %s;%s" % (name_str, type(name_str), type_str, type(type_str), comment, type(comment)))
		self.name = name
		self.type = type
		self.comment = comment
		# Additional fields
		self.enum = None
		self.switch = None
		self.compound = None

	def __repr__(self):
		comment = "" if self.comment is None else f" // {self.comment}"
		return f"Field({self.name}: {self.type}{comment})"

	def __str__(self):
		return f"Field({self.name}: {self.type})"


class Compound:
	"""A structure composed of fields"""

	def __init__(self, name, field=None):
		self.name = name
		self.entries = []
		self.field = field
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

	def __str__(self):
		return f"SwitchEntry({self.value} => {self.name})"


class Switch:
	"""The data changes depending on another field, which should be an enum"""
	entries: List[SwitchEntry]

	def __init__(self, field: Field):
		self.field = field
		field.switch = self
		self.entries = []
		self.name = first_up(field.name)

	def add_entry(self, entry: SwitchEntry):
		self.entries.append(entry)


	def __str__(self):
		return f"Switch{self.entries}"


class EnumEntry:
	def __init__(self, value, name, comment=None):
		self.value = value
		self.name = name
		self.comment = comment

	def __str__(self):
		return f"EnumEntry({self.name} = {self.value})"


class Enum:
	"""A field with a limited number of values, usually integers"""
	entries: List[EnumEntry]

	def __init__(self, field: Field):
		self.field = field
		field.enum = self
		self.entries = []
		self.name = first_up(field.name)

	def add_entry(self, entry: EnumEntry):
		self.entries.append(entry)


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


class PacketInfos:
	"""
	Stores data during the packet construction
	"""
	section: HtmlSection
	main_table: HtmlTable
	below_main: List[Any]
	main_compound: Compound  # not registered in dict_compounds
	main_id: int
	dict_fields: Dict[str, Field]  # contains also the sub-fields

	def __init__(self, section: HtmlSection):
		self.section = section
		t: HtmlTable
		i: int
		t, i = section.find_i(lambda x: isinstance(x, HtmlTable))
		self.main_table = t
		self.below_main = section.content[i + 1:]
		self.main_compound = Compound(classname(section.title))
		self.main_id = int(get_text(t.get(1, 0)), base=0)  # second row first column
		self.dict_fields = {}

	def register_field(self, field: Field):
		self.dict_fields[field.name.lower()] = field


class LocalContext:
	"""
	Stores local data during the packet construction
	"""
	notes_col: int
	types_col: int
	names_col: int
	rowlimit: int
	table: List[List[HtmlCell]]

	def __init__(self, table: HtmlTable, names_col, types_col, notes_col):
		self.table = table.rows
		self.rowlimit = table.row_count()
		self.names_col = 0 if names_col is None else names_col
		self.types_col = self.names_col + 1 if types_col is None else types_col
		self.notes_col = table.column_count() - 1 if notes_col is None else notes_col


def indent(l: list, s: str, level: int, newline=True):
	if newline:
		prefix = "\n" + ("|  " * level)
	else:
		prefix = "  " * level
	l.append(f"{prefix}{s}")


def str_compound_entries(l, c: Compound, level=0):
	for entry in c.entries:
		if isinstance(entry, Switch):
			str_switch(l, entry, level)
		elif isinstance(entry, Field):
			indent(l, f"Field {entry.name}: {entry.type}", level)
			if entry.enum is not None:
				str_enum(l, entry.enum, level + 1)
		else:
			indent(l, f"[UNKNOWN] {str(entry)}", level)


def str_compound(l, c: Compound, level=0, newline=True):
	fo = "" if c.field is None else f"for {c.field}"
	indent(l, f"Compound {c.name}{fo}", level, newline)
	str_compound_entries(l, c, level + 1)


def str_switch(l, s: Switch, level=0):
	indent(l, f"Switch {s.name} over {s.field}", level)
	for entry in s.entries:
		indent(l, f"{entry.value} => {entry.name}", level + 1)
		str_compound_entries(l, entry, level + 2)


def str_enum(l, e: Enum, level=0):
	indent(l, f"Enum {e.name}", level)
	for entry in e.entries:
		comment = "" if entry.comment is None else f" // {entry.comment}"
		indent(l, f"{entry.name} = {entry.value}{comment}", level + 1)
