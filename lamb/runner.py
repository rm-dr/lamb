from tkinter import E
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit import print_formatted_text as printf

import enum

import lamb.commands as commands
from lamb.parser import LambdaParser
import lamb.tokens as tokens
import lamb.utils as utils


class StopReason(enum.Enum):
	BETA_NORMAL		= ("class:text", "β-normal form")
	LOOP_DETECTED	= ("class:warn", "Loop detected")
	MAX_EXCEEDED	= ("class:err", "Too many reductions")
	INTERRUPT		= ("class:warn", "User interrupt")
	RECURSION		= ("class:err", "Python Recursion Error")


class Runner:
	def __init__(self, prompt_session: PromptSession, prompt_message):
		self.macro_table = {}
		self.prompt_session = prompt_session
		self.prompt_message = prompt_message
		self.parser = LambdaParser(
			action_command		= tokens.command.from_parse,
			action_macro_def	= tokens.macro_expression.from_parse,
			action_church		= tokens.church_num.from_parse,
			action_func			= tokens.lambda_func.from_parse,
			action_bound		= tokens.macro.from_parse,
			action_macro		= tokens.macro.from_parse,
			action_apply		= tokens.lambda_apply.from_parse
		)

		# Maximum amount of reductions.
		# If None, no maximum is enforced.
		# Must be at least 1.
		self.reduction_limit: int | None = 1_000_000

		# Ensure bound variables are unique.
		# This is automatically incremented whenever we make
		# a bound variable.
		self.bound_variable_counter = 0

	def prompt(self):
		return self.prompt_session.prompt(message = self.prompt_message)

	def parse(self, line):
		e = self.parser.parse_line(line)
		# Give the elements of this expression access to the runner.
		# Runner must be set BEFORE variables are bound.
		e.set_runner(self)
		if isinstance(e, tokens.macro_expression):
			e.bind_variables(ban_macro_name = e.label)
		else:
			e.bind_variables()
		return e


	def reduce_expression(self, expr: tokens.LambdaToken) -> None:

		# Reduction Counter.
		# We also count macro (and church) expansions,
		# and subtract those from the final count.
		i = 0
		macro_expansions = 0

		stop_reason = StopReason.MAX_EXCEEDED

		while (self.reduction_limit is None) or (i < self.reduction_limit):

			try:
				r = expr.reduce()
			except RecursionError:
				stop_reason = StopReason.RECURSION
				break
			expr = r.output

			#print(expr)
			#self.prompt()

			# If we can't reduce this expression anymore,
			# it's in beta-normal form.
			if not r.was_reduced:
				stop_reason = StopReason.BETA_NORMAL
				break

			# Count reductions
			#i += 1
			if (
					r.reduction_type == tokens.ReductionType.MACRO_EXPAND or
					r.reduction_type == tokens.ReductionType.AUTOCHURCH
				):
				macro_expansions += 1
			else:
				i += 1

		if (
			stop_reason == StopReason.BETA_NORMAL or
			stop_reason == StopReason.LOOP_DETECTED
			):
			out_str = str(r.output) # type: ignore

			printf(FormattedText([
				("class:result_header", f"\nExit reason: "),
				stop_reason.value,

				("class:result_header", f"\nMacro expansions: "),
				("class:text", str(macro_expansions)),

				("class:result_header", f"\nReductions: "),
				("class:text", str(i)),


				("class:result_header", "\n\n    => "),
				("class:text", out_str),
			]), style = utils.style)
		else:
			printf(FormattedText([
				("class:result_header", f"\nExit reason: "),
				stop_reason.value,

				("class:result_header", f"\nMacro expansions: "),
				("class:text", str(macro_expansions)),

				("class:result_header", f"\nReductions: "),
				("class:text", str(i)),
			]), style = utils.style)

	def save_macro(self, macro: tokens.macro_expression, *, silent = False) -> None:
		was_rewritten = macro.label in self.macro_table
		self.macro_table[macro.label] = macro.expr

		if not silent:
			printf(FormattedText([
				("class:text", "Set "),
				("class:syn_macro", macro.label),
				("class:text", " to "),
				("class:text", str(macro.expr))
			]), style = utils.style)

	# Apply a list of definitions
	def run(self, line: str, *, silent = False) -> None:
		e = self.parse(line)

		# If this line is a macro definition, save the macro.
		if isinstance(e, tokens.macro_expression):
			self.save_macro(e, silent = silent)

		# If this line is a command, do the command.
		elif isinstance(e, tokens.command):
			commands.run(e, self)

		# If this line is a plain expression, reduce it.
		elif isinstance(e, tokens.LambdaToken):
			self.reduce_expression(e)

		# We shouldn't ever get here.
		else:
			raise TypeError(f"I don't know what to do with a {type(e)}")


	def run_lines(self, lines: list[str]):
		for l in lines:
			self.run(l, silent = True)
