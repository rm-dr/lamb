from prompt_toolkit.formatted_text import FormattedText

import tokens
from parser import Parser
import commands
from runstatus import RunStatus
from runstatus import MacroStatus
from runstatus import StopReason
from runstatus import ReduceStatus
from runstatus import CommandStatus






class Runner:
	def __init__(self):
		self.macro_table = {}

		# Maximum amount of reductions.
		# If None, no maximum is enforced.
		self.reduction_limit: int | None = 300

	def exec_command(self, command: str) -> CommandStatus:
		if command in commands.commands:
			return commands.run(command, self)

		# Handle unknown commands
		else:
			return CommandStatus(
				formatted_text = FormattedText([
					("#FFFF00", f"Unknown command \"{command}\"")
				])
			)


	def reduce_expression(self, expr: tokens.LambdaToken) -> ReduceStatus:

		# Reduction Counter.
		# We also count macro expansions,
		# and subtract those from the final count.
		i = 0
		macro_expansions = 0

		while i < self.reduction_limit:
			r = expr.reduce(self.macro_table)
			expr = r.output

			# If we can't reduce this expression anymore,
			# it's in beta-normal form.
			if not r.was_reduced:
				return ReduceStatus(
					reduction_count = i - macro_expansions,
					stop_reason = StopReason.BETA_NORMAL,
					result = r.output
				)

			# Count reductions
			i += 1
			if r.reduction_type == tokens.ReductionType.MACRO_EXPAND:
				macro_expansions += 1

		return ReduceStatus(
			reduction_count = i - macro_expansions,
			stop_reason = StopReason.MAX_EXCEEDED,
			result = r.output
		)


	# Apply a list of definitions
	def run(self, line: str) -> RunStatus:
		e = Parser.parse_line(line)

		# If this line is a macro definition, save the macro.
		if isinstance(e, tokens.macro_expression):
			was_rewritten = e.label in self.macro_table

			e.exp.bind_variables()
			self.macro_table[e.label] = e.exp

			return MacroStatus(
				was_rewritten = was_rewritten,
				macro_label = e.label
			)

		# If this line is a command, do the command.
		elif isinstance(e, tokens.command):
			return self.exec_command(e.name)

		# If this line is a plain expression, reduce it.
		else:
			e.bind_variables()
			return self.reduce_expression(e)


	def run_lines(self, lines: list[str]):
		for l in lines:
			self.run(l)
