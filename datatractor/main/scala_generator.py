from datatractor.main.packets_extractor import Packet
from datatractor.utils.string_tools import *


def scala_type(field_type: str) -> str:
	"""
	Returns the Scala type that corresponds to the given packet field type.
	:param field_type: the (non-scala) field's type
	:return: the corresponding Scala type
	"""
	t: str = field_type.lower().replace("enum", "").strip()
	same = ["boolean", "byte", "short", "int", "long", "float", "double", "string"]
	as_str = ["chat", "identifier"]
	if t in same:
		return t.title()
	if t == "uuid":
		return "UUID"
	if ("string" in t) or (t in as_str):
		return "String"
	if (t == "varint") or (t == "unsigned byte") or (t == "unsigned short"):
		return "Int"
	if (t == "varlong") or (t == "position"):
		return "Long"
	if t == "entity metadata":
		# TODO support EntityMetadata storage
		return "AnyRef"
	if t == "slot":
		# TODO support items slots
		return "AnyRef"
	if t == "nbt tag":
		# TODO support nbt tags
		return "AnyRef"
	if t == "angle":
		return "Byte"
	if t == "no fields" or t == "no field":
		return "Nothing"

	if t.startswith("optional "):
		x = t[9:]
		scala_x = scala_type(x)
		return "Option[%s]" % scala_x
	if t.startswith("array of "):
		x = t[8:]
		scala_x = scala_type(x)
		return "Array[%s]" % scala_x
	if t.endswith(" array"):
		x = t[:-6]
		scala_x = scala_type(x)
		return "Array[%s]" % scala_x

	return "???"


def niol_write(field_type: str) -> str:
	"""
	Generates a Scala statement that writes the given field.
	:param field_type: the (non-scala) field's type
	:return: a code that writes the field
	"""
	t: str = field_type.lower().replace("enum", "").strip()
	simple_dict = {
		"boolean": "out.putBoolean($)",
		"byte": "out.putByte($)",
		"short": "out.putShort($)",
		"int": "out.putInt($)",
		"unsigned byte": "out.putInt($)",
		"unsigned short": "out.putInt($)",
		"long": "out.putLong($)",
		"float": "out.putFloat($)",
		"double": "out.putDouble($)",
		"string": "out.putString($, UTF_8)",
		"uuid": "out.putLong($.getMostSignificantBits); out.putLong($.getLeastSignificantBits)",
		"varint": "out.putVarint($)",
		"varlong": "out.putVarlong($)",
		"byte array": "out.putBytes($)",
		"array of byte": "out.putBytes($)",
		"array of int": "out.putInts($)",
		"array of long": "out.putLongs($)",
		"array of float": "out.putFloats($)",
		"array of double": "out.putDoubles($)",
	}
	simple = simple_dict.get(t)
	if simple:
		return simple

	if t.startswith("optional "):
		x = t[9:]
		write_x = niol_write(x)
		return "if ($.isDefined) {\n\t\t\t%s\n\t\t}" % write_x

	# TODO support more data types

	return "// TODO write $"


def niol_read(field_type: str, prefix: str = "val ") -> str:
	"""
	Generates a Scala statement that reads the given field.
	:param field_type: the (non-scala) field's type
	:param prefix: the prefix to append before the assignation of the value
	:return: a code that reads the field
	"""
	t: str = field_type.lower().replace("enum", "").strip()
	simple_dict = {
		"boolean": prefix + "$ = in.getBoolean()",
		"byte": prefix + "$ = in.getByte()",
		"short": prefix + "$ = in.getShort()",
		"int": prefix + "$ = in.getInt()",
		"long": prefix + "$ = in.getLong()",
		"float": prefix + "$ = in.getFloat()",
		"double": prefix + "$ = in.getDouble()",
		"uuid": prefix + "$ = new UUID(in.getLong(), in.getLong())",
		"varint": prefix + "$ = in.getVarint()",
		"varlong": prefix + "$ = in.getVarlong()",
		"unsigned byte": prefix + "$ = in.getUnsignedByte()",
		"unsigned short": prefix + "$ = in.getUnsignedShort()",
		"string": prefix + "$ = in.getString($Length, UTF_8)",
		"byte array": prefix + "$ = in.getBytes($Length)",
		"array of byte": prefix + "$ = in.getBytes($Length)",
		"array of int": prefix + "$ = in.getInts($Length)",
		"array of long": prefix + "$ = in.getLongs($Length)",
		"array of float": prefix + "$ = in.getFloats($Length)",
		"array of double": prefix + "$ = in.getLongs($Length)",
	}
	simple = simple_dict.get(t)
	if simple:
		return simple

	# TODO support more data types

	return "// TODO read $"


todo_count = 0


def generate_packet_class(p: Packet) -> (str, str):
	"""
	Generates scala classes from packet data.
	:param p: the packet
	:return: the name of the generated class, and the generated class (as a string)
	"""
	integers = ["Byte", "Short", "Int"]
	pname = p.name + "Packet"
	bname = pname + "Builder"
	decl = []
	write = []
	read = []
	construct = []
	b_decl = []
	b_with = []
	traits = []
	complete = [bname]
	has_uuid = False
	has_utf8 = False
	skip = False
	for i in range(len(p.fields)):
		if skip:
			skip = False
			continue
		field = p.fields[i]
		fname = field.name
		ftype = scala_type(field.type)
		is_length_field = False
		if ftype in integers and fname.endswith("Length") and i + 1 < len(p.fields):
			next_field = p.fields[i + 1]
			next_fname = next_field.name
			next_ftype = scala_type(next_field.type)
			if next_fname == fname[:-6]:  # fname without the "Length" at the end
				if next_ftype.startswith("Array"):  # type that has a length, except String (because in that case we have to get the utf8 byte count, not the character count)
					is_length_field = True
					skip = True
					length_field = field
					length_fname = fname
					length_ftype = ftype
					field = next_field
					fname = next_fname
					ftype = next_ftype
				else:
					print("WARNING - Unclear field %s - What is the \"length\" of a variable of type %s?" % (
						next_fname, next_ftype))
			else:
				print("WARNING - Unclear field %s: what field is it the length of?" % fname)

		if is_length_field:
			# Reads and writes the length before the actual value
			# The length field isn't in the constructor nor in the builder.
			length_fwrite = parametrize(niol_write(length_field.type), "$", fname + ".length")
			write.append("\t\t" + length_fwrite)

			length_fread = parametrize(niol_read(length_field.type), "$", length_fname)
			read.append("\t\t" + length_fread)

		name_and_type = "%s: %s" % (fname, ftype)

		has_uuid = has_uuid or ftype == "UUID"
		has_utf8 = has_utf8 or ftype == "String"

		decl.append("var " + name_and_type)
		b_decl.append("\tprivate[this] var %s = _" % name_and_type)

		if ftype == "String":
			if is_length_field:
				print("WARNING - Weird length field %s for a string whose length is implicit" % length_fname)

			bytes_fname = "%sBytes" % fname
			lwrite = "val %s = UTF_8.encode(%s)" % (bytes_fname, fname)
			lwrite2 = "out.putVarint(%s.limit)" % bytes_fname
			fwrite = "out.putBytes(%s)" % bytes_fname
			write.append("\t\t" + lwrite)
			write.append("\t\t" + lwrite2)
			write.append("\t\t" + fwrite)

			lread = parametrize(niol_read("varint"), "$", fname + "Length")
			fread = parametrize(niol_read("string"), "$", fname)
			read.append("\t\t" + lread)
			read.append("\t\t" + fread)
		else:
			fwrite = parametrize(niol_write(field.type), "$", fname)
			write.append("\t\t" + fwrite)

			fread = parametrize(niol_read(field.type), "$", fname)
			read.append("\t\t" + fread)

		global todo_count
		if "TODO" in fwrite:
			todo_count += 1
		if "TODO" in fread:
			todo_count += 1

		construct.append(fname)

		fcapital = to_pascal_case(field.name_snake)
		with1 = "\tdef with%s(%s): %s[P with %s] {" % (fcapital, name_and_type, bname, fcapital)
		with2 = "\t\tthis.%s = %s" % (fname, fname)
		with3 = "\t\tthis.asInstanceOf[%s[P with %s]]" % (bname, fcapital)
		with4 = "\t}"
		b_with.append("\n".join([with1, with2, with3, with4]))

		traits.append("sealed trait %s" % fcapital)
		complete.append(fcapital)

	fields_declaration = ", ".join(decl)
	fields_writing = "\n".join(write)
	fields_reading = "\n".join(read)
	packet_constructing = ", ".join(construct)
	import_uuid = "import java.util.UUID\n" if has_uuid else ""
	import_utf8 = "import java.nio.charset.StandardCharsets.UTF_8\n" if has_utf8 else ""
	builder_fields = "\n".join(b_decl)
	builder_setters = "\n\n".join(b_with)
	traits_declaration = "\n\t".join(traits)
	mixin_declaration = " with ".join(complete)

	# TODO import tuubes.core.network.packets or something like this

	pclass = """
import com.electronwill.niol.{NiolInput, NiolOutput}
%s%s
/** Packet class auto-generated by DataTractor */
final class %s(%s) extends Packet {
	override def write(out: NiolOutput): Unit {
%s
	}
	
	override def id = %s.id
	
}
object %s extends PacketObj {
	override val id = %d
	
	override def read(in: NiolOutput): %s {
%s
		new %s(%s)
	}
}
/** Packet builder auto-generated by DataTractor */
final class %s[P <: %s] extends PacketBuilder[%s] {
%s

%s

	override def build()(implicit evidence: P =:= Complete) {
		new %s(%s)
	}
}
object %s {
	%s
	type Complete = %s
}
""" % (import_uuid, import_utf8,
	   pname, fields_declaration,
	   fields_writing,
	   pname,
	   pname,
	   p.id,
	   pname,
	   fields_reading,
	   pname, packet_constructing,

	   bname, pname, pname,
	   builder_fields,
	   builder_setters,
	   pname, packet_constructing,
	   bname,
	   traits_declaration,
	   mixin_declaration
	   )

	return pname, pclass.strip()


def write_packet_class(folder, packet):
	pname, pclass = generate_packet_class(packet)
	output_file = "%s/%s.scala" % (folder, pname)
	f = open(output_file, "w+")
	f.write(pclass)
	f.close()
