from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit import print_formatted_text as printf
import enum
import math
import time

import lamb


class StopReason(enum.Enum):
	BETA_NORMAL		= ("class:text", "β-normal form")
	LOOP_DETECTED	= ("class:warn", "Loop detected")
	MAX_EXCEEDED	= ("class:err", "Too many reductions")
	INTERRUPT		= ("class:warn", "User interrupt")

class MacroDef:
	@staticmethod
	def from_parse(result):
		return MacroDef(
			result[0].name,
			result[1]
		)

	def __init__(self, label: str, expr: lamb.node.Node):
		self.label = label
		self.expr = expr

	def __repr__(self):
		return f"<{self.label} := {self.expr!r}>"

	def __str__(self):
		return f"{self.label} := {self.expr}"

	def bind_variables(self, *, ban_macro_name = None):
		return self.expr.bind_variables(
			ban_macro_name = ban_macro_name
		)

	def set_runner(self, runner):
		return self.expr.set_runner(runner)

class Command:
	@staticmethod
	def from_parse(result):
		return Command(
			result[0],
			result[1:]
		)

	def __init__(self, name, args):
		self.name = name
		self.args = args


class Runner:
	def __init__(
		self,
		prompt_session: PromptSession,
		prompt_message
	):
		self.macro_table = {}
		self.prompt_session = prompt_session
		self.prompt_message = prompt_message
		self.parser = lamb.parser.LambdaParser(
			action_func = lamb.node.Func.from_parse,
			action_bound = lamb.node.Macro.from_parse,
			action_macro = lamb.node.Macro.from_parse,
			action_call = lamb.node.Call.from_parse,
			action_church = lamb.node.Church.from_parse,
			action_macro_def = MacroDef.from_parse,
			action_command = Command.from_parse,
			action_history = lamb.node.History.from_parse
		)

		# Maximum amount of reductions.
		# If None, no maximum is enforced.
		# Must be at least 1.
		self.reduction_limit: int | None = 1_000_000

		# Ensure bound variables are unique.
		# This is automatically incremented whenever we make
		# a bound variable.
		self.bound_variable_counter = 0

		# Update iteration after this many iterations
		# Make sure every place value has a non-zero digit
		# so that all digits appear to be changing.
		self.iter_update = 231

		self.history = []

	def prompt(self):
		return self.prompt_session.prompt(
			message = self.prompt_message
		)

	def parse(self, line) -> tuple[lamb.node.Node | MacroDef | Command, dict]:
		e = self.parser.parse_line(line)

		o = {}
		if isinstance(e, MacroDef):
			e.set_runner(self)
			o = e.bind_variables(ban_macro_name = e.label)
		elif isinstance(e, lamb.node.Node):
			e.set_runner(self)
			o = e.bind_variables()
		return e, o


	def reduce(self, node: lamb.node.Node, *, status = {}) -> None:

		warning_text = []

		# Reduction Counter.
		# We also count macro (and church) expansions,
		# and subtract those from the final count.
		k = 0
		macro_expansions = 0

		stop_reason = StopReason.MAX_EXCEEDED
		start_time = time.time()
		out_text = []

		if status["has_history"] and len(self.history) != 0:
			warning_text += [
				("class:code", "$"),
				("class:warn", " will be expanded to "),
				("class:code", str(self.history[-1])),
				("class:warn", "\n")
			]

		only_macro = isinstance(node, lamb.node.ExpandableEndNode)
		if only_macro:
			warning_text += [
				("class:warn", "All macros will be expanded"),
				("class:warn", "\n")
			]
		m, node = lamb.node.expand(node, force_all = only_macro)
		macro_expansions += m


		for i in status["free_variables"]:
			warning_text += [
				("class:warn", "Name "),
				("class:code", i),
				("class:warn", " is a free variable\n"),
			]

		printf(FormattedText(warning_text), style = lamb.utils.style)


		while (self.reduction_limit is None) or (k < self.reduction_limit):

			# Show reduction count
			if (k >= self.iter_update) and (k % self.iter_update == 0):
				print(f" Reducing... {k:,}", end = "\r")

			try:
				red_type, node = lamb.node.reduce(node)
			except KeyboardInterrupt:
				stop_reason = StopReason.INTERRUPT
				break

			# If we can't reduce this expression anymore,
			# it's in beta-normal form.
			if red_type == lamb.node.ReductionType.NOTHING:
				stop_reason = StopReason.BETA_NORMAL
				break

			# Count reductions
			k += 1
			if red_type == lamb.node.ReductionType.FUNCTION_APPLY:
				macro_expansions += 1

		if k >= self.iter_update:
			# Clear reduction counter if it was printed
			print(" " * round(14 + math.log10(k)), end = "\r")

		out_text += [
			("class:result_header", f"Runtime: "),
			("class:text", f"{time.time() - start_time:.03f} seconds"),

			("class:result_header", f"\nExit reason: "),
			stop_reason.value,

			("class:result_header", f"\nMacro expansions: "),
			("class:text", f"{macro_expansions:,}"),

			("class:result_header", f"\nReductions: "),
			("class:text", f"{k:,}\t"),
			("class:muted", f"(Limit: {self.reduction_limit:,})")
		]

		if (stop_reason == StopReason.BETA_NORMAL or stop_reason == StopReason.LOOP_DETECTED):
			out_text += [
				("class:result_header", "\n\n    => "),
				("class:text", str(node)), # type: ignore
			]

			self.history.append(lamb.node.expand(node, force_all = True)[1])


		printf(
			FormattedText(out_text),
			style = lamb.utils.style
		)

	def save_macro(
			self,
			macro: MacroDef,
			*,
			silent = False
		) -> None:
		was_rewritten = macro.label in self.macro_table
		self.macro_table[macro.label] = macro.expr

		if not silent:
			printf(FormattedText([
				("class:text", "Set "),
				("class:syn_macro", macro.label),
				("class:text", " to "),
				("class:text", str(macro.expr))
			]), style = lamb.utils.style)

	# Apply a list of definitions
	def run(
			self,
			line: str,
			*,
			silent = False
		) -> None:
		e, o = self.parse(line)

		# If this line is a macro definition, save the macro.
		if isinstance(e, MacroDef):
			self.save_macro(e, silent = silent)

		# If this line is a command, do the command.
		elif isinstance(e, Command):
			if e.name not in lamb.commands.commands:
				printf(
					FormattedText([
						("class:warn", f"Unknown command \"{e.name}\"")
					]),
					style = lamb.utils.style
				)
			else:
				lamb.commands.commands[e.name](e, self)

		# If this line is a plain expression, reduce it.
		elif isinstance(e, lamb.node.Node):
			self.reduce(e, status = o)

		# We shouldn't ever get here.
		else:
			raise TypeError(f"I don't know what to do with a {type(e)}")


	def run_lines(self, lines: list[str]):
		for l in lines:
			self.run(l, silent = True)
