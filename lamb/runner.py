from prompt_toolkit import PromptSession

import lamb.commands as commands
from lamb.parser import LambdaParser
import lamb.tokens as tokens
import lamb.utils as utils
import lamb.runstatus as rs


class Runner:
	def __init__(self, prompt_session: PromptSession, prompt_message):
		self.macro_table = {}
		self.prompt_session = prompt_session
		self.prompt_message = prompt_message
		self.parser = LambdaParser(
			action_command		= tokens.command.from_parse,
			action_macro_def	= tokens.macro_expression.from_parse,
			action_church		= utils.autochurch(self),
			action_func			= tokens.lambda_func.from_parse,
			action_bound		= tokens.macro.from_parse,
			action_macro		= tokens.macro.from_parse,
			action_apply		= tokens.lambda_apply.from_parse
		)

		# Maximum amount of reductions.
		# If None, no maximum is enforced.
		self.reduction_limit: int | None = 300

		# Ensure bound variables are unique.
		# This is automatically incremented whenever we make
		# a bound variable.
		self.bound_variable_counter = 0

	def prompt(self):
		return self.prompt_session.prompt(message = self.prompt_message)


	def reduce_expression(self, expr: tokens.LambdaToken) -> rs.ReduceStatus:

		# Reduction Counter.
		# We also count macro expansions,
		# and subtract those from the final count.
		i = 0
		macro_expansions = 0

		while (self.reduction_limit is None) or (i < self.reduction_limit):
			print(repr(expr))
			r = expr.reduce()
			expr = r.output

			# If we can't reduce this expression anymore,
			# it's in beta-normal form.
			if not r.was_reduced:
				return rs.ReduceStatus(
					reduction_count = i - macro_expansions,
					stop_reason = rs.StopReason.BETA_NORMAL,
					result = r.output
				)

			# Count reductions
			i += 1
			if r.reduction_type == tokens.ReductionType.MACRO_EXPAND:
				macro_expansions += 1

		return rs.ReduceStatus(
			reduction_count = i - macro_expansions,
			stop_reason = rs.StopReason.MAX_EXCEEDED,
			result = r.output # type: ignore
		)


	# Apply a list of definitions
	def run(self, line: str, *, macro_only = False) -> rs.RunStatus:
		e = self.parser.parse_line(line)
		# Give the elements of this expression access to the runner.
		# Runner must be set BEFORE variables are bound.
		e.set_runner(self)
		e.bind_variables()

		# If this line is a macro definition, save the macro.
		if isinstance(e, tokens.macro_expression):
			was_rewritten = e.label in self.macro_table
			self.macro_table[e.label] = e.exp

			return rs.MacroStatus(
				was_rewritten = was_rewritten,
				macro_label = e.label,
				macro_expr = e.exp
			)

		elif macro_only:
			raise rs.NotAMacro()

		# If this line is a command, do the command.
		elif isinstance(e, tokens.command):
			commands.run(e, self)
			return rs.CommandStatus(cmd = e.name)

		# If this line is a plain expression, reduce it.
		elif isinstance(e, tokens.LambdaToken):
			return self.reduce_expression(e)

		# We shouldn't ever get here.
		else:
			raise TypeError(f"I don't know what to do with a {type(e)}")


	def run_lines(self, lines: list[str]):
		for l in lines:
			self.run(l)
