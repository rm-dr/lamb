import tokens
from parser import Parser
import enum


class RunStatus:
	"""
	Base class for run status.
	These are returned whenever the runner does something.
	"""
	pass

class MacroStatus(RunStatus):
	"""
	Returned when a macro is defined.

	Values:
	`was_rewritten`:	If true, an old macro was replaced.
	`macro_label`:		The name of the macro we just made.
	"""

	def __init__(
		self,
		*,
		was_rewritten: bool,
		macro_label: str
	):
		self.was_rewritten = was_rewritten
		self.macro_label = macro_label


class StopReason(enum.Enum):
	BETA_NORMAL		= ("#FFFFFF", "β-normal form")
	LOOP_DETECTED	= ("#FFFF00", "loop detected")
	MAX_EXCEEDED	= ("#FFFF00", "too many reductions")
	INTERRUPT		= ("#FF0000", "user interrupt")


class ReduceStatus(RunStatus):
	"""
	Returned when an expression is reduced.

	Values:
	`reduction_count`:	How many reductions were made.
	`stop_reason`:		Why we stopped. See `StopReason`.
	"""

	def __init__(
		self,
		*,
		reduction_count: int,
		stop_reason: StopReason,
		result: tokens.LambdaToken
	):
		self.reduction_count = reduction_count
		self.stop_reason = stop_reason
		self.result = result


class Runner:
	def __init__(self):
		self.macro_table = {}

		# Maximum amount of reductions.
		# If None, no maximum is enforced.
		self.reduction_limit: int | None = 300

	def exec_command(self, command: str):
		if command == "help":
			print("This is a help message.")

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
