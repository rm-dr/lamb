from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit import prompt
from prompt_toolkit import print_formatted_text as printf
import enum
import math
import time

import lamb

from lamb.runner.misc import MacroDef
from lamb.runner.misc import Command
from lamb.runner.misc import StopReason
from lamb.runner import commands as cmd


# Keybindings for step prompt.
# Prevents any text from being input.
step_bindings = KeyBindings()
@step_bindings.add("<any>")
def _(event):
	pass


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
			action_func = lamb.nodes.Func.from_parse,
			action_bound = lamb.nodes.Macro.from_parse,
			action_macro = lamb.nodes.Macro.from_parse,
			action_call = lamb.nodes.Call.from_parse,
			action_church = lamb.nodes.Church.from_parse,
			action_macro_def = MacroDef.from_parse,
			action_command = Command.from_parse,
			action_history = lamb.nodes.History.from_parse
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

		self.history: list[lamb.nodes.Root] = []

		# If true, reduce step-by-step.
		self.step_reduction = False

		# If true, expand ALL macros when printing output
		self.full_expansion = False

	def prompt(self):
		return self.prompt_session.prompt(
			message = self.prompt_message
		)

	def parse(self, line) -> tuple[lamb.nodes.Root | MacroDef | Command, list]:
		e = self.parser.parse_line(line)

		w = []
		if isinstance(e, MacroDef):
			e.expr = lamb.nodes.Root(e.expr)
			e.set_runner(self)
			w = lamb.nodes.prepare(e.expr, ban_macro_name = e.label)
		elif isinstance(e, lamb.nodes.Node):
			e = lamb.nodes.Root(e)
			e.set_runner(self)
			w = lamb.nodes.prepare(e)

		return e, w


	def reduce(self, node: lamb.nodes.Root, *, warnings = []) -> None:

		# Reduction Counter.
		# We also count macro (and church) expansions,
		# and subtract those from the final count.
		k = 0
		macro_expansions = 0

		stop_reason = StopReason.MAX_EXCEEDED
		start_time = time.time()
		out_text = []

		only_macro = (
			isinstance(node.left, lamb.nodes.Macro) or
			isinstance(node.left, lamb.nodes.Church)
		)
		if only_macro:
			stop_reason = StopReason.SHOW_MACRO
		m, node = lamb.nodes.expand(node, force_all = only_macro)
		macro_expansions += m

		if len(warnings) != 0:
			printf(FormattedText(warnings), style = lamb.utils.style)

		if self.step_reduction:
			printf(FormattedText([
				("class:warn", "Step-by-step reduction is enabled.\n"),
				("class:muted", "Press "),
				("class:cmd_key", "ctrl-c"),
				("class:muted", " to continue automatically.\n"),
				("class:muted", "Press "),
				("class:cmd_key", "enter"),
				("class:muted", " to step.\n"),
			]), style = lamb.utils.style)


		skip_to_end = False
		while (
				(
					(self.reduction_limit is None) or
					(k < self.reduction_limit)
				) and not only_macro
			):

			# Show reduction count
			if (
					( (k >= self.iter_update) and (k % self.iter_update == 0) )
					and not (self.step_reduction and not skip_to_end)
				):
				print(f" Reducing... {k:,}", end = "\r")

			try:
				red_type, node = lamb.nodes.reduce(node)
			except KeyboardInterrupt:
				stop_reason = StopReason.INTERRUPT
				break

			# If we can't reduce this expression anymore,
			# it's in beta-normal form.
			if red_type == lamb.nodes.ReductionType.NOTHING:
				stop_reason = StopReason.BETA_NORMAL
				break

			# Count reductions
			k += 1
			if red_type == lamb.nodes.ReductionType.FUNCTION_APPLY:
				macro_expansions += 1

			# Pause after step if necessary
			if self.step_reduction and not skip_to_end:
				try:
					s = prompt(
						message = FormattedText([
							("class:muted", lamb.nodes.reduction_text[red_type]),
							("class:muted", f":{k:03} "),
							("class:text", str(node)),
						]),
						style = lamb.utils.style,
						key_bindings = step_bindings
					)
				except KeyboardInterrupt or EOFError:
					skip_to_end = True
					printf(FormattedText([
						("class:warn", "Skipping to end."),
					]), style = lamb.utils.style)

		# Print a space between step messages
		if self.step_reduction:
			print("")

		# Clear reduction counter if it was printed
		if k >= self.iter_update:
			print(" " * round(14 + math.log10(k)), end = "\r")

		# Expand fully if necessary
		if self.full_expansion:
			o, node = lamb.nodes.expand(node, force_all = True)
			macro_expansions += o

		if only_macro:
			out_text += [
				("class:ok", f"Displaying macro content")
			]

		else:
			out_text += [
				("class:ok", f"Runtime: "),
				("class:text", f"{time.time() - start_time:.03f} seconds"),

				("class:ok", f"\nExit reason: "),
				stop_reason.value,

				("class:ok", f"\nMacro expansions: "),
				("class:text", f"{macro_expansions:,}"),

				("class:ok", f"\nReductions: "),
				("class:text", f"{k:,}\t"),
				("class:muted", f"(Limit: {self.reduction_limit:,})")
			]

		if self.full_expansion:
			out_text += [
				("class:ok", "\nAll macros have been expanded")
			]

		if (
				stop_reason == StopReason.BETA_NORMAL or
				stop_reason == StopReason.LOOP_DETECTED or
				only_macro
		):
			out_text += [
				("class:ok", "\n\n    => "),
				("class:text", str(node)), # type: ignore
			]


		printf(
			FormattedText(out_text),
			style = lamb.utils.style
		)

		# Save to history
		# Do this at the end so we don't always fully expand.
		self.history.append(lamb.nodes.expand(node, force_all = True)[1])

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
				("class:code", macro.label),
				("class:text", " to "),
				("class:code", str(macro.expr))
			]), style = lamb.utils.style)

	# Apply a list of definitions
	def run(
			self,
			line: str,
			*,
			silent = False
		) -> None:
		e, w = self.parse(line)

		# If this line is a macro definition, save the macro.
		if isinstance(e, MacroDef):
			self.save_macro(e, silent = silent)

		# If this line is a command, do the command.
		elif isinstance(e, Command):
			if e.name not in cmd.commands:
				printf(
					FormattedText([
						("class:warn", f"Unknown command \"{e.name}\"")
					]),
					style = lamb.utils.style
				)
			else:
				cmd.commands[e.name](e, self)

		# If this line is a plain expression, reduce it.
		elif isinstance(e, lamb.nodes.Node):
			self.reduce(e, warnings = w)

		# We shouldn't ever get here.
		else:
			raise TypeError(f"I don't know what to do with a {type(e)}")


	def run_lines(self, lines: list[str]):
		for l in lines:
			self.run(l, silent = True)
