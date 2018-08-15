import re


def camel_case(snake_str: str) -> str:
	# Converts snake_case to camelCase by capitalizing the first letter of each part except the first one
	parts = snake_str.split('_')
	return parts[0] + ''.join(x.title() for x in parts[1:])


def pascal_case(snake_str: str) -> str:
	# Converts snake_case to PascalCase by capitalizing the first letter of each part
	parts = snake_str.split('_')
	return ''.join(x.title() for x in parts)


def snake_case(s: str) -> str:
	return s.lower().replace(" ", "_")


def varname(name: str):
	rep = {"/": "_or_", "-": "minus", "+": "plus", "type": "typ", " ": "_"}
	return camel_case(multireplace(name, rep))


def classname(name: str):
	rep = {"/": "_or_", "-": "", "+": "", " ": "_"}
	return pascal_case(multireplace(re.sub("\(.*?\)", "", name), rep))


def plural(noun: str):
	last = noun[-1]
	if last == "y":
		return noun[:-1] + "ies"
	elif last == "h":
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
