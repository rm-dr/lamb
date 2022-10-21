import pyparsing as pp
import tokens

class Parser:
	"""
	Macro_def must be on its own line.
	macro_def  :: var = expr

	var        :: word
	lambda_fun :: var -> expr
	call       :: '(' (var | expr) ')' +
	expr       :: define | var | call | '(' expr ')'
	"""

	lp = pp.Suppress("(")
	rp = pp.Suppress(")")

	# Simple tokens
	pp_expr = pp.Forward()
	pp_name = pp.Word(pp.alphas + "_")
	pp_name.set_parse_action(tokens.macro.from_parse)

	# Function definitions.
	# Right associative.
	#
	# <var> => <exp>
	pp_lambda_fun = (pp.Suppress("λ") | pp.Suppress("\\")) + pp_name + pp.Suppress(".") + pp_expr
	pp_lambda_fun.set_parse_action(tokens.lambda_func.from_parse)

	# Assignment.
	# Can only be found at the start of a line.
	#
	# <var> = <exp>
	pp_macro_def = pp.line_start() + pp_name + pp.Suppress("=") + pp_expr
	pp_macro_def.set_parse_action(tokens.macro_expression.from_parse)

	# Function calls.
	# `tokens.lambda_func.from_parse` handles chained calls.
	#
	# <var>(<exp>)
	# <var>(<exp>)(<exp>)(<exp>)
	# (<exp>)(<exp>)
	# (<exp>)(<exp>)(<exp>)(<exp>)
	pp_call = pp.Forward()
	pp_call <<= pp_expr[2, ...]
	pp_call.set_parse_action(tokens.lambda_apply.from_parse)

	pp_expr <<= pp_lambda_fun ^ (lp + pp_expr + rp) ^ pp_name ^ (lp + pp_call + rp)
	pp_all = pp_expr | pp_macro_def

	pp_command = ":" + pp_name
	pp_command.set_parse_action(tokens.command.from_parse)

	@staticmethod
	def parse_line(line):
		k = (
			Parser.pp_expr ^
			Parser.pp_macro_def ^
			Parser.pp_command ^ Parser.pp_call
		).parse_string(
			line,
			parse_all = True
		)[0]
		print(k)
		return(k)

	@staticmethod
	def run_tests(lines):
		return Parser.pp_macro_def.run_tests(lines)