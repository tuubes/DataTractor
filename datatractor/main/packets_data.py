from typing import Any, Dict, Optional

from utils.html_tools import *
from utils.string_tools import *


class Field:
	"""A field"""
	name: str
	type: str
	comment: str
	string_max_length: Optional[int]
	length_given_by: Optional  # Optional[Field]
	is_length_of: Optional  # Optional[Field]
	only_if: Optional[str]
	only_if_bool: Optional  # Optional[Field]
	is_condition_of: Optional  # Optional[Field]

	def __init__(self, name: str, type: str, comment: str, string_max_length: Optional[int] = None):
		# DEBUG print("Field: %s:%s, %s:%s, %s;%s" % (name_str, type(name_str), type_str, type(type_str), comment, type(comment)))
		self.name = name
		self.type = type
		self.comment = comment
		self.string_max_length = string_max_length
		self.length_given_by = None
		self.is_length_of = None
		self.only_if = None
		self.only_if_bool = None
		self.is_condition_of = None
		# Additional fields
		self.enum = None
		self.switch = None
		self.compound = None

	def __repr__(self):
		return str(self)

	def __str__(self):
		comment = "" if self.comment is None else f" // {self.comment}"
		maxlen = "" if self.string_max_length is None else f" (length <= {self.string_max_length})"
		lengiv = "" if self.length_given_by is None else f" (length given by {self.length_given_by.type} {self.length_given_by.name})"
		return f"Field({self.name}: {self.type}{maxlen}{lengiv}{comment})"

	def json(self):
		return f'{{' \
			   f'"dataType": "Field",' \
			   f'"name": "{self.name}",' \
			   f'"type": "{self.type}",' \
			   f'"comment": "{self.comment}",' \
			   f'"stringMaxLength": {jsonize(self.string_max_length)},' \
			   f'"lengthGivenBy": {"null" if self.length_given_by is None else jsonize(self.length_given_by.name)}' \
			   f'"onlyIf": {"null" if self.only_if is None else jsonize(self.only_if)}' \
			   f'"enum": {jsonize(self.enum)},' \
			   f'"switch": {jsonize(self.switch)},' \
			   f'"compound": {jsonize(self.compound)}' \
			   f'}}'

	def set_length_given_by(self, field):
		self.length_given_by = field
		field.is_length_of = self


class Compound:
	"""A structure composed of fields"""
	fields_dict: Dict[str, Field]
	is_ref_out: bool  # True if this compound contains a Switch with is_ref_out == True

	def __init__(self, name, field=None):
		self.name = name
		self.entries = []
		self.fields_dict = {}
		self.is_ref_out = False
		self.field = field
		if field is not None:
			field.compound = self

	def add_field(self, field: Field):
		self.entries.append(field)
		self.fields_dict[field.name.lower()] = field

	def add_switch(self, switch):
		self.entries.append(switch)
		if switch.is_ref_out:
			self.is_ref_out = True

	def is_empty(self):
		return len(self.entries) == 0

	def json(self):
		return f'{{' \
			   f'"dataType": "Compound",' \
			   f'"name": "{self.name}",' \
			   f'"field": {jsonize(self.field)},' \
			   f'"entries": {jsonize(self.entries)}' \
			   f'}}'


class SwitchEntry(Compound):
	"""Switch entry"""

	def __init__(self, value, name):
		super().__init__(name)
		self.value = value

	def __str__(self):
		return f"SwitchEntry({self.value} => {self.name})"

	def json(self):
		return f'{{' \
			   f'"dataType": "SwitchEntry",' \
			   f'"name": "{self.name}",' \
			   f'"value": {jsonize(self.value)}' \
			   f'"field": {jsonize(self.field)},' \
			   f'"entries": {jsonize(self.entries)}' \
			   f'}}'


class Switch:
	"""The data changes depending on another field, which should be an enum"""
	entries: List[SwitchEntry]
	is_ref_out: bool  # True if the field we refer to is outside of the compound that contains the switch

	def __init__(self, field: Field, is_ref_out):
		self.field = field
		field.switch = self
		self.entries = []
		self.is_ref_out = is_ref_out
		self.name = first_up(field.name)
		self.id_field_name = "typeId" if field.name == "typ" else f"{field.name}Id"

	def add_entry(self, entry: SwitchEntry):
		self.entries.append(entry)

	def __str__(self):
		return f"Switch{self.entries}"

	def json(self):
		return f'{{' \
			   f'"dataType": "Switch",' \
			   f'"name": "{self.name}",' \
			   f'"field": {jsonize(self.field)},' \
			   f'"entries": {jsonize(self.entries)}' \
			   f'}}'


class EnumEntry:
	def __init__(self, value, name, comment=None):
		self.value = value
		self.name = name
		self.comment = comment

	def __str__(self):
		return f"EnumEntry({self.name} = {self.value})"

	def json(self):
		return f'{{' \
			   f'"dataType": "EnumEntry",' \
			   f'"name": "{self.name}",' \
			   f'"value": {jsonize(self.value)},' \
			   f'"comment": {jsonize(self.comment)}' \
			   f'}}'


_imposed_names = {
	"typ": "Type",
	"slot": "SlotEnum"
}


class Enum:
	"""A field with a limited number of values, usually integers"""
	entries: List[EnumEntry]

	def __init__(self, field: Field):
		self.field = field
		field.enum = self
		self.entries = []
		imposed = _imposed_names.get(field.name)
		self.name = imposed if imposed is not None else first_up(field.name)

	def add_entry(self, entry: EnumEntry):
		self.entries.append(entry)

	def json(self):
		return f'{{' \
			   f'"dataType": "Enum",' \
			   f'"name": "{self.name}",' \
			   f'"field": {jsonize(self.field)},' \
			   f'"entries": {jsonize(self.entries)}' \
			   f'}}'


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

	def json(self):
		return f'{{' \
			   f'"dataType": "Protocol",' \
			   f'"gameVersion": "{self.game_version}",' \
			   f'"number": {self.number},' \
			   f'"play": {jsonize(self.play)},' \
			   f'"status": {jsonize(self.status)},' \
			   f'"login": {jsonize(self.login)}' \
			   f'}}'


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

	def json(self):
		return f'{{' \
			   f'"dataType": "SubProtocol",' \
			   f'"name": "{self.name}",' \
			   f'"clientBound": {jsonize(self.clientbound)},' \
			   f'"serverBound": {jsonize(self.serverbound)},' \
			   f'}}'


class PacketInfos:
	"""
	Stores data during the packet construction
	"""
	section: HtmlSection
	main_table: HtmlTable
	below_main: List[Any]
	main_compound: Compound
	main_id: int
	dict_fields: Dict[str, Field]
	all_fields: List[Field]  # contains all the fields we've found

	def __init__(self, section: HtmlSection):
		self.section = section
		t: HtmlTable
		i: int
		t, i = section.find_i(lambda x: isinstance(x, HtmlTable))
		self.main_table = t
		self.below_main = section.content[i + 1:]
		self.main_compound = Compound(classname(section.title))
		self.main_id = int(get_text(t.get(1, 0)), base=0)  # second row first column
		self.all_fields = []
		self.dict_fields = {}

	def register_field(self, field: Field):
		self.all_fields.append(field)
		self.dict_fields[field.name.lower()] = field

	def name(self):
		return self.main_compound.name

	def id(self):
		return self.main_id

	def json(self):
		return f'{{' \
			   f'"dataType": "PacketInfos",' \
			   f'"id": {self.main_id},' \
			   f'"compound": {self.main_compound.json()},' \
			   f'}}'


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
			maxlen = "" if entry.string_max_length is None else f" (length <= {entry.string_max_length})"
			lengiv = "" if entry.length_given_by is None else f" (length given by {entry.length_given_by.type} {entry.length_given_by.name})"
			onlyif = "" if entry.only_if is None else f" (ONLY IF {entry.only_if})"
			indent(l, f"Field {entry.name}: {entry.type}{maxlen}{lengiv}{onlyif}", level)
			if entry.compound is not None:
				str_compound(l, entry.compound, level + 1)
			if entry.enum is not None:
				str_enum(l, entry.enum, level + 1)
		else:
			indent(l, f"[UNKNOWN] {str(entry)}", level)


def str_compound(l, c: Compound, level=0, newline=True):
	fo = "" if c.field is None else f" for {c.field}"
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
