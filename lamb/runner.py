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
			action_command = Command.from_parse
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

	def prompt(self):
		return self.prompt_session.prompt(
			message = self.prompt_message
		)

	def parse(self, line):
		e = self.parser.parse_line(line)

		if isinstance(e, MacroDef):
			e.bind_variables(ban_macro_name = e.label)
		elif isinstance(e, lamb.node.Node):
			e.bind_variables()
		return e


	def reduce(self, node: lamb.node.Node) -> None:
		# Reduction Counter.
		# We also count macro (and church) expansions,
		# and subtract those from the final count.
		i = 0
		macro_expansions = 0

		stop_reason = StopReason.MAX_EXCEEDED
		start_time = time.time()

		while (self.reduction_limit is None) or (i < self.reduction_limit):

			# Show reduction count
			if (i >= self.iter_update) and (i % self.iter_update == 0):
				print(f" Reducing... {i}", end = "\r")

			try:
				red_type, new_node = lamb.node.reduce(
					node,
					macro_table = self.macro_table
				)
			except KeyboardInterrupt:
				stop_reason = StopReason.INTERRUPT
				break

			node = new_node

			# If we can't reduce this expression anymore,
			# it's in beta-normal form.
			if red_type == lamb.node.ReductionType.NOTHING:
				stop_reason = StopReason.BETA_NORMAL
				break

			# Count reductions
			i += 1
			if red_type == lamb.node.ReductionType.FUNCTION_APPLY:
				macro_expansions += 1

		if i >= self.iter_update:
			# Clear reduction counter
			print(" " * round(14 + math.log10(i)), end = "\r")

		out_text = [
			("class:result_header", f"\nRuntime: "),
			("class:text", f"{time.time() - start_time:.03f} seconds"),

			("class:result_header", f"\nExit reason: "),
			stop_reason.value,

			("class:result_header", f"\nMacro expansions: "),
			("class:text", str(macro_expansions)),

			("class:result_header", f"\nReductions: "),
			("class:text", f"{i}    "),
			("class:muted", f"(Limit: {self.reduction_limit:,})")
		]

		if (stop_reason == StopReason.BETA_NORMAL or stop_reason == StopReason.LOOP_DETECTED):
			out_text += [
				("class:result_header", "\n\n    => "),
				("class:text", str(new_node)), # type: ignore
			]

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
		e = self.parse(line)

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
			self.reduce(e)

		# We shouldn't ever get here.
		else:
			raise TypeError(f"I don't know what to do with a {type(e)}")


	def run_lines(self, lines: list[str]):
		for l in lines:
			self.run(l, silent = True)
