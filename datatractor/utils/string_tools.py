def to_camel_case(snake_str: str):
	# Converts snake_case to camelCase by capitalizing the first letter of each part except the first one
	parts = snake_str.split('_')
	return parts[0] + ''.join(x.title() for x in parts[1:])


def to_snake_case(s: str):
	return s.lower().replace(" ", "_")


def parametrize(val: str, placeholder: str, param: str):
	if param:
		return val.replace(placeholder, param)
	else:
		return val
