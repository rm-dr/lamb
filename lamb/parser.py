import pyparsing as pp

import lamb.tokens as tokens
import lamb.utils as utils

class Parser:
	lp = pp.Suppress("(")
	rp = pp.Suppress(")")

	# Simple tokens
	pp_expr = pp.Forward()
	pp_macro = pp.Word(pp.alphas + "_")
	pp_macro.set_parse_action(tokens.macro.from_parse)

	pp_church = pp.Word(pp.nums)
	pp_church.set_parse_action(utils.autochurch)

	# Function calls.
	# `tokens.lambda_apply.from_parse` handles chained calls.
	#
	# <exp> <exp>
	# <exp> <exp> <exp>
	pp_call = pp.Forward()
	pp_call <<= pp_expr[2, ...]
	pp_call.set_parse_action(tokens.lambda_apply.from_parse)

	# Function definitions.
	# Right associative.
	#
	# <var> => <exp>
	pp_lambda_fun = (
		(pp.Suppress("λ") | pp.Suppress("\\")) +
		pp.Group(pp.Char(pp.alphas)[1, ...]) +
		pp.Suppress(".") +
		(pp_expr ^ pp_call)
	)
	pp_lambda_fun.set_parse_action(tokens.lambda_func.from_parse)

	# Assignment.
	# Can only be found at the start of a line.
	#
	# <name> = <exp>
	pp_macro_def = (
		pp.line_start() +
		pp_macro +
		pp.Suppress("=") +
		(pp_expr ^ pp_call)
	)
	pp_macro_def.set_parse_action(tokens.macro_expression.from_parse)

	pp_expr <<= (
		pp_church ^
		pp_lambda_fun ^
		pp_macro ^
		(lp + pp_expr + rp) ^
		(lp + pp_call + rp)
	)

	pp_command = pp.Suppress(":") + pp.Word(pp.alphas + "_")
	pp_command.set_parse_action(tokens.command.from_parse)


	pp_all = (
		pp_expr ^
		pp_macro_def ^
		pp_command ^
		pp_call
	)

	@staticmethod
	def parse_line(line):
		return Parser.pp_all.parse_string(
			line,
			parse_all = True
		)[0]

	@staticmethod
	def run_tests(lines):
		return Parser.pp_all.run_tests(lines)