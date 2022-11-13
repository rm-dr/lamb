import pyparsing as pp

# Packrat gives a significant speed boost.
pp.ParserElement.enablePackrat()

class LambdaParser:
	def make_parser(self):
		self.lp = pp.Suppress("(")
		self.rp = pp.Suppress(")")
		self.pp_expr = pp.Forward()

		# Bound variables are ALWAYS lowercase and single-character.
		# We still create macro objects from them, they are turned into
		# bound variables after the expression is built.
		self.pp_macro = pp.Word(pp.alphas + "_")
		self.pp_bound = pp.Regex("[a-z][₀₁₂₃₄₅₆₈₉]*")
		self.pp_name = self.pp_bound ^ self.pp_macro
		self.pp_church = pp.Word(pp.nums)
		self.pp_history = pp.Char("$")

		# Function calls.
		#
		# <exp> <exp>
		# <exp> <exp> <exp>
		self.pp_call = pp.Forward()
		self.pp_call <<= (self.pp_expr | self.pp_bound | self.pp_history)[2, ...]

		# Function definitions, right associative.
		# Function args MUST be lowercase.
		#
		# <var> => <exp>
		self.pp_lambda_fun = (
			(pp.Suppress("λ") | pp.Suppress("\\")) +
			pp.Group(self.pp_bound[1, ...]) +
			pp.Suppress(".") +
			(self.pp_expr ^ self.pp_call)
		)

		# Assignment.
		# Can only be found at the start of a line.
		#
		# <name> = <exp>
		self.pp_macro_def = (
			pp.line_start() +
			self.pp_macro +
			pp.Suppress("=") +
			(self.pp_expr ^ self.pp_call ^ self.pp_history)
		)

		self.pp_expr <<= (
			self.pp_church ^
			self.pp_lambda_fun ^
			self.pp_name ^
			(self.lp + self.pp_expr + self.rp) ^
			(self.lp + self.pp_call + self.rp) ^
			(self.lp + self.pp_history + self.rp)
		)

		self.pp_command = pp.Suppress(":") + pp.Word(pp.alphas + "_") + pp.Word(pp.printables)[0, ...]


		self.pp_all = (
			self.pp_expr ^
			self.pp_macro_def ^
			self.pp_command ^
			self.pp_call ^
			self.pp_history
		)

	def __init__(
			self,
			*,
			action_command,
			action_macro_def,
			action_church,
			action_func,
			action_bound,
			action_macro,
			action_call,
			action_history
		):

		self.make_parser()

		self.pp_command.set_parse_action(action_command)
		self.pp_macro_def.set_parse_action(action_macro_def)
		self.pp_church.set_parse_action(action_church)
		self.pp_lambda_fun.set_parse_action(action_func)
		self.pp_macro.set_parse_action(action_macro)
		self.pp_bound.set_parse_action(action_bound)
		self.pp_call.set_parse_action(action_call)
		self.pp_history.set_parse_action(action_history)

	def parse_line(self, line: str):
		return self.pp_all.parse_string(
			line,
			parse_all = True
		)[0]

	def run_tests(self, lines: list[str]):
		return self.pp_all.run_tests(lines)