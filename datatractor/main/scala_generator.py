from typing import Union

from datatractor.main.packets_extractor import *

output = "out"
input = "in"
_imports = ["com.electronwill.niol.{NiolInput, NiolOutput}"
			"org.tuubes.minecraft.protocol.common._"
			"org.tuubes.minecraft.protocol.common.nbt._"]
line_max = -1


def init(version: str, output_name="out", input_name="in", max_line_length=100):
	global output
	global input
	global base_package
	output = output_name
	input = input_name
	v = version.replace('.', '_')
	base_package = f"org.tuubes.minecraft.protocol.{v}"
	_imports.append(f"org.tuubes.minecraft.protocol.{v}.utils._")

	global line_max
	line_max = max_line_length


def write_packet_class(p: PacketInfos, filepath: str, fullpackage=None, subpackage=None):
	package = fullpackage if fullpackage else (f"{base_package}.{subpackage}" if subpackage else "???")
	pclass = gen_compound_class(p.main_compound, 0, parent="Packet")
	pobject = gen_compound_object(p.main_compound, 0, parent="PacketObj", additional=f"def id = {p.id()}")
	with open(filepath, mode="w+") as f:
		f.write(f"package {package}\n\n")
		f.write(pclass)
		f.write(pobject)


def write_protocol_class(p: SubProtocol, filepath: str, importsubpackage: str, fullpackage=None, subpackage=None):
	package = fullpackage if fullpackage else (f"{base_package}.{subpackage}" if subpackage else "???")
	serverbound_packet_count = len(p.serverbound)
	serverbound_packet_regs = [f"  ingoingPackets({packet.id()}) = {packet.name()}" for packet in p.serverbound]
	packet_registrations = '\n'.join(serverbound_packet_regs)
	with open(filepath, mode="w+") as f:
		f.write(f"package {package}\n\n")
		f.write("import org.tuubes.minecraft.protocol.MCJavaProtocol\n")
		f.write(f"import {base_package}.{importsubpackage}._\n\n")
		f.write(f"object {first_up(p.name.lower())}Protocol extends MCJavaProtocol({serverbound_packet_count}) {{\n"
				f"{packet_registrations}\n"
				f"}}")


def write_simple(typ, var):
	return f"{output}.put{typ}({var})"


def read_simple(typ, var):
	return f"{var} = {input}.get{typ}()"


def write_bulk(typ, var):
	return f"{output}.put{type_param(typ)}s({var})"


def read_bulk(typ, var):
	return f"{var} = {input}.get{type_param(typ)}s()"


def write_option(x: Field, typ, var, indent_level):
	condition = x.only_if if (x.only_if and not x.only_if_bool) else f"{var}.isDefined"
	code = statement_write(x, indent_level + 1, type_param(typ), f"{var}.get")
	_ = "  " * indent_level
	return f"{_}if ({condition}) {{\n" \
		   f"{code}\n" \
		   f"{_}}}"


def read_option(x: Field, typ: str, var, indent_level):
	condition = x.only_if if x.only_if else f"false /* TODO */"
	var_value = f"{var}Value"
	code = statement_read(x, indent_level + 1, type_param(typ), var_value)
	_ = "  " * indent_level
	___ = "  " + _
	return f"{_}val {var} = if ({condition}) {{\n" \
		   f"{code}\n" \
		   f"{___}Some({var_value})\n" \
		   f"{_}}} else {{\n" \
		   f"{___}None\n" \
		   f"{_}}}"


def write_array(x: Field, typ: str, var, indent_level):
	length = x.length_given_by
	elem_type = type_param(typ)
	elem_var = f"{var}(i)"
	_ = "  " * indent_level
	___ = "  " + _
	return f"{_};{{\n" \
		   f"{___}var i = 0\n" \
		   f"{___}while (i < {var}.length) {{\n" \
		   f"{statement_write(x, indent_level + 2, elem_type, elem_var)}\n" \
		   f"{___}  i += 1\n" \
		   f"{___}}}\n" \
		   f"{_}}}"


def read_array(x: Field, typ: str, var, indent_level):
	if x.length_given_by is None:
		return f"// TODO read array {var}"
	length = x.length_given_by.name
	elem_type = type_param(typ)
	elem_var = f"{var}(i)"
	_ = "  " * indent_level
	___ = "  " + _
	return f"{_}val {var} = new {typ}({length})\n" \
		   f"{_};{{\n" \
		   f"{___}var i = 0\n" \
		   f"{___}while (i < {length}) {{\n" \
		   f"{statement_read(x, indent_level + 2, elem_type, elem_var, do_add_val=False)}\n" \
		   f"{___}  i += 1\n" \
		   f"{___}}}\n" \
		   f"{_}}}"


__writes = {
	"Boolean": write_simple,
	"Byte": write_simple,
	"Short": write_simple,
	"Int": write_simple,
	"Varint": write_simple,
	"Long": write_simple,
	"Varlong": write_simple,
	"Float": write_simple,
	"Double": write_simple,
	"UUID": write_simple,
	"UnsignedByte": (lambda typ, var: f"{output}.putByte({var})"),
	"UnsignedShort": (lambda typ, var: f"{output}.putShort({var})"),
	"String": (lambda typ, var: f"{output}.putVarstring({var})"),
	"Slot": (lambda typ, var: f"{var}.writeTo({output})"),
	"Tag": (lambda typ, var: f"{var}.writeNamed({output})"),
	"Position": (lambda typ, var: f"{output}.putLong(Conversions.packPosition({var}))"),
	"Angle": (lambda typ, var: f"{output}.putByte(Conversions.radiansToRotationSteps({var})"),
	"Array[Byte]": write_bulk,
	"Array[Short]": write_bulk,
	"Array[Int]": write_bulk,
	"Array[Long]": write_bulk,
	"Array[Float]": write_bulk,
	"Array[Double]": write_bulk,
	"Array[UnsignedByte]": (lambda typ, var: read_bulk("Array[Byte]", var)),
	"Array[UnsignedShort]": (lambda typ, var: read_bulk("Array[Short]", var)),
}

__reads = {
	"Boolean": read_simple,
	"Byte": read_simple,
	"Short": read_simple,
	"Int": read_simple,
	"Varint": read_simple,
	"Long": read_simple,
	"Varlong": read_simple,
	"Float": read_simple,
	"Double": read_simple,
	"UUID": read_simple,
	"UnsignedByte": (lambda typ, var: f"{var} = {input}.getUnsignedByte()"),
	"UnsignedShort": (lambda typ, var: f"{var} = {input}.getUnsignedShort()"),
	"String": (lambda typ, var: f"{var} = {input}.getVarstring()"),
	"Slot": (lambda typ, var: f"{var} = Slot.readFrom({input})"),
	"Tag": (lambda typ, var: f"{var} = Tag.readNamed({input})"),
	"Position": (lambda typ, var: f"{var} = Conversions.unpackPosition({input}.getLong())"),
	"Angle": (lambda typ, var: f"{var} = Conversions.rotationStepsToRadians({input}.getByte())"),
	"Array[Byte]": read_bulk,
	"Array[Short]": read_bulk,
	"Array[Int]": read_bulk,
	"Array[Long]": read_bulk,
	"Array[Float]": read_bulk,
	"Array[Double]": read_bulk,
	"Array[UnsignedByte]": (lambda typ, var: read_bulk("Array[Byte]", var)),
	"Array[UnsignedShort]": (lambda typ, var: read_bulk("Array[Short]", var)),
}

__types_full_replacements = {
	"EntityMetadata": "NiolOutput => Unit",
	"Chat": "String",
	"Identifier": "String",
	"NbtTag": "Tag",
	"Uuid": "UUID",
	"Integer": "Int"
}
__types_decl_replacements = {
	**__types_full_replacements,
	"Array[UnsignedByte]": "Array[Byte]",  # use a byte array to use less memory
	"Array[UnsignedShort]": "Array[Short]",  # use a short array to use less memory
	"UnsignedByte": "Int",
	"UnsignedShort": "Int",
	"Varint": "Int",
	"Varlong": "Long",
	"Angle": "Float",
	"Position": "Vec3i"
}

__types_to_ignore = ["Void", "Unit", "Nothing"]

__bulk_arrays = ["Array[Byte]", "Array[Short]", "Array[Int]", "Array[Long]", "Array[Float]", "Array[Double]",
				 "Array[UnsignedByte]", "Array[UnsignedShort]"]


def type_for_use(t: str):
	return multireplace(t, __types_full_replacements)


def type_for_declaration(x: Field):
	if x.switch is not None:
		return x.switch.name
	new_type = multireplace(x.type, __types_decl_replacements)
	if new_type != x.type:
		x.comment = f"Original type: {x.type}" if not x.comment else f"{x.comment}. Original type: {x.type}"
	return new_type


def declaration(field: Field):
	t = type_for_declaration(field)
	return f"var {field.name}: {t}"


def statement_write(entry: Union[Field, Switch], indent_level: int, typ=None, var=None) -> str:
	a: str
	_ = "  " * indent_level
	if isinstance(entry, Switch):
		entry: Switch
		a = f"{entry.field.name}.writeTo({output})"
	else:
		entry: Field
		typ = type_for_use(entry.type if typ is None else typ)
		if typ in __types_to_ignore:
			return f"{_}// Nothing to write for type {typ}"

		var = entry.name if var is None else var
		if entry and entry.switch:
			var += "Id"
		elif entry and entry.is_length_of:
			var = f"{entry.is_length_of.name}.length"

		if typ.startswith("Option["):
			return write_option(entry, typ, var, indent_level)
		elif typ.startswith("Array[") and typ not in __bulk_arrays:
			return write_array(entry, typ, var, indent_level)
		else:
			f = __writes.get(typ)
			if f is None:
				a = f"{var}.writeTo({output})"
			elif entry and entry.switch:
				a = f(typ, f"{var}.id")
			else:
				a = f(typ, var)
	return f"{_}{a}"


def statement_read(entry: Union[Field, Switch], indent_level: int, typ=None, var=None, do_add_val=True) -> str:
	a: str
	_ = "  " * indent_level
	if isinstance(entry, Switch):
		entry: Switch
		a = f"{entry.field.name} = {entry.name}.readFrom({input}, {entry.field.name}Id)"
	else:
		entry: Field
		typ = type_for_use(entry.type if typ is None else typ)
		if typ in __types_to_ignore:
			return f"{_}// Nothing to read for type {typ}"

		var = entry.name if var is None else var
		if entry and entry.switch:
			var += "Id"

		if typ.startswith("Option["):
			return read_option(entry, typ, var, indent_level)
		elif typ.startswith("Array[") and typ not in __bulk_arrays:
			return read_array(entry, typ, var, indent_level)
		else:
			a: str
			f = __reads.get(typ)
			if f is None:
				a = f"{var} = {typ}.readFrom({input})"
			elif entry and entry.switch:
				a = f"{f(typ, var)}"
			else:
				a = f(typ, var)
	prefix = "val " if do_add_val else ""
	return f"{_}{prefix}{a}"


def gen_compound_class(c: Compound,
					   indent_level: int,
					   do_import=False,
					   parent: Optional[str] = "Writeable",
					   additional: Optional[str] = None) -> str:
	indent = "  " * indent_level
	indent1 = "  " + indent
	indent2 = "  " + indent1
	lfields = []
	lwrites = []
	lswitches = []  # Contains only the switches that need to be in the class, usually they're in the companion object
	lcompounds = []  # Contains only the compounds that need to be in the class, ...
	for entry in c.entries:
		if isinstance(entry, Field) and entry.is_condition_of:
			var = f"{entry.is_condition_of.name}.isDefined"
			lwrites.append(statement_write(None, indent_level + 2, "Boolean", var))
		else:
			lwrites.append(statement_write(entry, indent_level + 2))
		if isinstance(entry, Field):
			# Don't store the array's length as a separate field, it will be stored by the array
			# Also, don't store the optional's condition when it's a simple boolean
			# And remove the Void types
			if entry.is_length_of is None and entry.is_condition_of is None and entry.type not in __types_to_ignore:
				lfields.append(declaration(entry))
				if entry.compound is not None and entry.compound.is_ref_out:
					lcompounds.append(gen_compound_class(entry.compound, indent_level + 1))
		elif isinstance(entry, Switch):
			if entry.is_ref_out:
				lswitches.append(gen_switch(entry, indent_level + 1))
		else:  # should not happen
			print(f"[WARNING] Unknown entry of type {type(entry)} in compound {c.name}")
	imports = '\n'.join(_imports) if do_import else ""
	extends = f"extends {parent} " if parent else ""
	additional_code = f"{indent1}{additional}\n" if additional else ""

	fields = ", ".join(lfields)
	writes = '\n'.join(lwrites)
	switches = '\n'.join(lswitches)
	compounds = '\n'.join(lcompounds)

	fields_decl = f"({fields})" if fields else ""
	writes_code = f"\n{writes}\n{indent1}" if writes else ""
	switches_code = f"\n{switches}" if switches else ""
	compounds_code = f"\n{compounds}" if compounds else ""
	class_start = f"class {c.name}"
	class_declaration = f"{indent}class {c.name}{fields_decl} {extends}{{"
	if len(class_declaration) > line_max:
		fields = f"\n{indent}{' ' * (len(class_start)+1)}".join(lfields)
		fields_decl = f"({fields})"
	return f"{indent}class {c.name}{fields_decl} {extends}{{\n" \
		   f"{additional_code}" \
		   f"{indent1}def writeTo({output}: NiolOutput): Unit = {{{writes_code}}}\n" \
		   f"{compounds_code}" \
		   f"{switches_code}" \
		   f"{indent}}}\n"


def gen_compound_object(c: Compound,
						indent_level: int,
						is_parent_generic=True,
						parent="Reader",
						additional: Optional[str] = None) -> str:
	indent = "  " * indent_level
	indent1 = "  " + indent
	indent2 = "  " + indent1
	lparams = []
	lreads = []
	lenums = []
	lswitches = []  # Doesn't contain the switches that need to be in the class (see gen_compound_class)
	lcompounds = []  # Doesn't contain the compounds that need to be in the class
	for entry in c.entries:
		lreads.append(statement_read(entry, indent_level + 2))
		if isinstance(entry, Field):
			# Don't store the array's length as a separate field, it will be stored by the array
			# Also, don't store the optional's condition when it's a simple boolean
			# And remove the Void types
			if entry.is_length_of is None and entry.is_condition_of is None and entry.type not in __types_to_ignore:
				lparams.append(entry.name)
				if entry.enum is not None:
					lenums.append(gen_enum(entry.enum, indent_level + 1))
				elif entry.compound is not None and not entry.compound.is_ref_out:
					clazz = gen_compound_class(entry.compound, indent_level + 1)
					companion = gen_compound_object(entry.compound, indent_level + 1)
					lcompounds.append(f"{clazz}{companion}")  # there's a \n at the end of clazz
		elif isinstance(entry, Switch):
			if not entry.is_ref_out:
				lswitches.append(gen_switch(entry, indent_level + 1))
		else:  # should not happen
			print(f"[WARNING] Unknown entry of type {type(entry)} in compound {c.name}")

	extends = f"extends {parent}[{c.name}] " if is_parent_generic else f"extends {parent} "
	additional_code = f"{indent1}{additional}\n" if additional else ""
	params = ", ".join(lparams) if lparams else ""
	construct = f"new {c.name}({params})"

	reads = '\n'.join(lreads)
	inner = '\n'.join(lenums + lcompounds + lswitches)

	reads_code = f"{{\n{reads}\n{indent2}{construct}\n{indent1}}}" if reads else f"{construct}"
	inner_code = f"\n{inner}" if inner else ""
	return f"{indent}object {c.name} {extends}{{\n" \
		   f"{additional_code}" \
		   f"{indent1}def readFrom({input}: NiolInput): {c.name} = {reads_code}\n" \
		   f"{inner_code}" \
		   f"{indent}}}\n"


def gen_switch_object(s: Switch, indent_level: int) -> str:
	indent = "  " * indent_level
	indent1 = "  " + indent
	indent2 = "  " + indent1
	indent3 = "  " + indent2
	lcases = []
	for entry in s.entries:
		entry_lreads = []
		entry_lparams = []
		for ee in entry.entries:
			entry_lreads.append(statement_read(ee, indent_level + 3))
			if isinstance(ee, Field) and ee.is_length_of is None and ee.is_condition_of is None:
				entry_lparams.append(ee.name)

		entry_params = ", ".join(entry_lparams) if entry_lparams else ""
		entry_construct = f"new {entry.name}({entry_params})"

		entry_reads = '\n'.join(entry_lreads)
		entry_reads_code = f"{entry_reads}\n{indent3}{entry_construct}" if entry_reads else f"{indent3}{entry_construct}"
		lcases.append(f"{indent2}case {entry.value} =>\n{entry_reads_code}")

	cases = '\n'.join(lcases)

	return f"{indent}object {s.name} {{\n" \
		   f"{indent1}def readFrom({input}: NiolInput, switchId: Int): {s.name} = switchId match {{\n" \
		   f"{cases}\n" \
		   f"{indent1}}}\n" \
		   f"{indent}}}"


def gen_switch(s: Switch, indent_level: int) -> str:
	_ = "  " * indent_level
	lentries = []
	for entry in s.entries:
		id_code = f"def id = {entry.value}"
		lentries.append(gen_compound_class(entry, indent_level, parent=s.name, additional=id_code))

	entries = "".join(lentries)
	object_code = gen_switch_object(s, indent_level)
	return f"{_}sealed trait {s.name} extends Writeable\n" \
		   f"{object_code}\n" \
		   f"{entries}"


def gen_enum(en: Enum, indent_level: int) -> str:
	_ = "  " * indent_level
	lvalues = []
	for e in en.entries:
		comment = "" if e.comment is None else f"{_}  /** {e.comment} */\n"
		lvalues.append(f"{comment}{_}  final val {e.name} = {e.value}")
	values = '\n'.join(lvalues)
	return f"{_}final class {en.name} {{\n" \
		   f"{values}\n" \
		   f"{_}}}\n"
