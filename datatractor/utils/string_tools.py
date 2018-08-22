import re


def camel_case(snake_str: str) -> str:
	# Converts snake_case to camelCase by capitalizing the first letter of each part except the first one
	parts = snake_str.split('_')
	return parts[0] + ''.join(first_up(x) for x in parts[1:])


def pascal_case(snake_str: str) -> str:
	# Converts snake_case to PascalCase by capitalizing the first letter of each part
	parts = snake_str.split('_')
	return ''.join(first_up(x) for x in parts)


def snake_case(s: str) -> str:
	return s.lower().replace(' ', '_')


def valid_field_name(name: str):
	low = name.strip().lower()
	if low == "type":
		return "typ"
	else:
		if low[0].isdigit():
			low = "_" + low
		rep = {'/': '_', '-': "minus", '+': "plus", '.': '_', ')': "", ':': "_", '–': "", ' ': '_'}
		return multireplace(low, rep).replace("___", "_or_")


def varname(name: str):
	return camel_case(valid_field_name(name))


def constname(name: str):
	f = valid_field_name(name)
	return "TYPE" if f == "typ" else f.upper()  # 'TYPE' upper-case is a valid Scala name


def classname(name: str):
	rep = {'/': '_', '-': "", '+': "", '.': "", ':': "", ' ': '_'}
	f = multireplace(re.sub("\(.*?\)", "", name.lower()), rep)
	return "Type" if f == "typ" else pascal_case(f)  # 'Type' with a capital 'T' is a valid Scala name


def __type(name: str):
	if name.startswith("array_of") or name.startswith("optional"):
		return name
	else:
		if ',' in name:
			s = name.split(',', maxsplit=1)
			if len(s[0]) == 0:
				name = s[1]
			else:
				name = s[0]
		if name[0] == '_':
			name = name[1:]
		if name[-1] == '_':
			name = name[:-1]
		return pascal_case(name)


def typename(name: str):
	rep = {"_enum": "", "enum": "", '/': '_', '-': "", '.': "", '+': "", ':': "", ' ': '_'}
	res = multireplace(name.lower(), rep)
	if res == "optional,_varies":
		return "Optional[Any]"
	res = re.sub(r"array_of(.{2,})s$", lambda m: f"Array[{__type(m.group(1))}]", res)  # remove the plural
	res = re.sub(r"array_of(.+)", lambda m: f"Array[{__type(m.group(1))}]", res)
	res = re.sub(r"optional(.+)", lambda m: f"Option[{__type(m.group(1))}]", res)
	res = re.sub(r"(.+)array", lambda m: f"Array[{__type(m.group(1))}]", res)
	return pascal_case(res.strip())


def first_up(s: str):
	return s[:1].upper() + s[1:]


def plural(noun: str):
	last = noun[-1]
	if last == 's':
		return noun
	elif last == 'y':
		return noun[:-1] + "ies"
	elif last == 'h':
		return noun[:-1] + "es"
	else:
		return noun + "s"


def parametrize(val: str, placeholder: str, param: str) -> str:
	if param:
		return val.replace(placeholder, param)
	else:
		return val


def multireplace(string, replacements) -> str:
	"""
	<From: https://gist.github.com/bgusach/a967e0587d6e01e889fd1d776c5f3729>
	Given a string and a replacement map, it returns the replaced string.
	:param str string: string to execute replacements on
	:param dict replacements: replacement dictionary {value to find: value to replace}
	:rtype: str
	"""
	# Place longer ones first to keep shorter substrings from matching where the longer ones should take place
	# For instance given the replacements {'ab': 'AB', 'abc': 'ABC'} against the string 'hey abc', it should produce
	# 'hey ABC' and not 'hey ABc'
	substrs = sorted(replacements, key=len, reverse=True)

	# Create a big OR regex that matches any of the substrings to replace
	regexp = re.compile('|'.join(map(re.escape, substrs)))

	# For each match, look up the new string in the replacements
	return regexp.sub(lambda match: replacements[match.group(0)], string)


def max_str_len(matrix):
	max_length = 0
	for row in matrix:
		for cell in row:
			max_length = max(max_length, len(str(cell)))
	return max_length


def max_str_len_bycolumn(matrix):
	nrows = len(matrix)
	ncols = len(matrix[0])
	maximums = [0] * ncols
	for j in range(0, ncols):
		for i in range(0, nrows):
			cell = matrix[i][j]
			maximums[j] = max(maximums[j], len(str(cell)))
	return maximums


def pretty_matrix_str(matrix):
	if len(matrix) == 0:
		return ""
	lengths = max_str_len_bycolumn(matrix)
	res = []
	for row in matrix:
		line = []
		j = 0
		for element in row:
			line.append(str(element).center(lengths[j]))
			j += 1
		res.append(" | ".join(line))
	return "\n".join(res)


def jsonize(s):
	if s is None:
		return "null"
	if isinstance(s, int):
		return str(s)
	elif isinstance(s, float):
		return str(s)
	elif isinstance(s, bool):
		return str(s).lower()
	elif isinstance(s, str):
		return f'"{str(s)}"'
	elif isinstance(s, list):
		content = ",".join([jsonize(e) for e in s])
		return f'[{content}]'
	else:
		return s.json()
