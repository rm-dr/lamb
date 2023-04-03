from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit import prompt
from prompt_toolkit import print_formatted_text as printf
import collections
import math
import time

import lamb_engine

from lamb_engine.runner.misc import MacroDef
from lamb_engine.runner.misc import Command
from lamb_engine.runner.misc import StopReason
from lamb_engine.runner import commands as cmd


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
		self.parser = lamb_engine.parser.LambdaParser(
			action_func = lamb_engine.nodes.Func.from_parse,
			action_bound = lamb_engine.nodes.Macro.from_parse,
			action_macro = lamb_engine.nodes.Macro.from_parse,
			action_call = lamb_engine.nodes.Call.from_parse,
			action_church = lamb_engine.nodes.Church.from_parse,
			action_macro_def = MacroDef.from_parse,
			action_command = Command.from_parse,
			action_history = lamb_engine.nodes.History.from_parse
		)

		# Maximum amount of reductions.
		# If None, no maximum is enforced.
		# Must be at least 1.
		self.reduction_limit = 1_000_000

		# Ensure bound variables are unique.
		# This is automatically incremented whenever we make
		# a bound variable.
		self.bound_variable_counter = 0

		# Update iteration after this many iterations
		# Make sure every place value has a non-zero digit
		# so that all digits appear to be changing.
		self.iter_update = 231

		self.history = collections.deque(
			[None] * 10,
			10)


		# If true, reduce step-by-step.
		self.step_reduction = False

		# If true, expand ALL macros when printing output
		self.full_expansion = False

	def prompt(self):
		return self.prompt_session.prompt(
			message = self.prompt_message
		)

	def parse(self, line): # -> tuple[lamb_engine.nodes.Root | MacroDef | Command, list]
		e = self.parser.parse_line(line)

		w = []
		if isinstance(e, MacroDef):
			e.expr = lamb_engine.nodes.Root(e.expr)
			e.set_runner(self)
			w = lamb_engine.nodes.prepare(e.expr, ban_macro_name = e.label)
		elif isinstance(e, lamb_engine.nodes.Node):
			e = lamb_engine.nodes.Root(e)
			e.set_runner(self)
			w = lamb_engine.nodes.prepare(e)

		return e, w


	def reduce(self, node: lamb_engine.nodes.Root, *, warnings = []) -> None:

		# Reduction Counter.
		# We also count macro (and church) expansions,
		# and subtract those from the final count.
		k = 0
		macro_expansions = 0

		stop_reason = StopReason.MAX_EXCEEDED
		start_time = time.time()
		out_text = []

		only_macro = (
			isinstance(node.left, lamb_engine.nodes.Macro) or
			isinstance(node.left, lamb_engine.nodes.Church)
		)
		if only_macro:
			stop_reason = StopReason.SHOW_MACRO
		m, node = lamb_engine.nodes.expand(node, force_all = only_macro)
		macro_expansions += m

		if len(warnings) != 0:
			printf(FormattedText(warnings), style = lamb_engine.utils.style)

		if self.step_reduction:
			printf(FormattedText([
				("class:warn", "Step-by-step reduction is enabled.\n"),
				("class:muted", "Press "),
				("class:cmd_key", "ctrl-c"),
				("class:muted", " to continue automatically.\n"),
				("class:muted", "Press "),
				("class:cmd_key", "enter"),
				("class:muted", " to step.\n"),
			]), style = lamb_engine.utils.style)


		skip_to_end = False
		try:
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

				# Reduce
				red_type, node = lamb_engine.nodes.reduce(node)

				# If we can't reduce this expression anymore,
				# it's in beta-normal form.
				if red_type == lamb_engine.nodes.ReductionType.NOTHING:
					stop_reason = StopReason.BETA_NORMAL
					break

				# Count reductions
				k += 1
				if red_type == lamb_engine.nodes.ReductionType.FUNCTION_APPLY:
					macro_expansions += 1

				# Pause after step if necessary
				if self.step_reduction and not skip_to_end:
					try:
						s = prompt(
							message = FormattedText([
								("class:prompt", lamb_engine.nodes.reduction_text[red_type]),
								("class:prompt", f":{k:03} ")
							] + lamb_engine.utils.lex_str(str(node))),
							style = lamb_engine.utils.style,
							key_bindings = step_bindings
						)
					except KeyboardInterrupt or EOFError:
						skip_to_end = True
						printf(FormattedText([
							("class:warn", "Skipping to end."),
						]), style = lamb_engine.utils.style)

		# Gracefully catch keyboard interrupts
		except KeyboardInterrupt:
			stop_reason = StopReason.INTERRUPT

		# Print a space between step messages
		if self.step_reduction:
			print("")

		# Clear reduction counter if it was printed
		if k >= self.iter_update:
			print(" " * round(14 + math.log10(k)), end = "\r")

		# Expand fully if necessary
		if self.full_expansion:
			o, node = lamb_engine.nodes.expand(node, force_all = True)
			macro_expansions += o

		if only_macro:
			out_text += [
				("class:ok", f"Displaying macro content")
			]

		else:
			if not self.step_reduction:
				out_text += [
					("class:ok", f"Runtime: "),
					("class:text", f"{time.time() - start_time:.03f} seconds"),
					("class:text", "\n")
				]

			out_text += [
				("class:ok", f"Exit reason: "),
				stop_reason.value,
				("class:text", "\n"),

				("class:ok", f"Macro expansions: "),
				("class:text", f"{macro_expansions:,}"),
				("class:text", "\n"),

				("class:ok", f"Reductions: "),
				("class:text", f"{k:,}\t"),
				("class:muted", f"(Limit: {self.reduction_limit:,})")
			]

		if self.full_expansion:
			out_text += [
				("class:text", "\n"),
				("class:ok", "All macros have been expanded")
			]

		if (
				stop_reason == StopReason.BETA_NORMAL or
				stop_reason == StopReason.LOOP_DETECTED or
				only_macro
		):
			out_text += [
				("class:ok", "\n\n    => ")
			] + lamb_engine.utils.lex_str(str(node))


		printf(
			FormattedText(out_text),
			style = lamb_engine.utils.style
		)

		# Save to history
		# Do this at the end so we don't always fully expand.
		self.history.appendleft(
			lamb_engine.nodes.expand( # type: ignore
				node,
				force_all = True
			)[1]
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
				("class:code", macro.label),
				("class:text", " to "),
				("class:code", str(macro.expr))
			]), style = lamb_engine.utils.style)

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
					style = lamb_engine.utils.style
				)
			else:
				cmd.commands[e.name](e, self)

		# If this line is a plain expression, reduce it.
		elif isinstance(e, lamb_engine.nodes.Node):
			self.reduce(e, warnings = w)

		# We shouldn't ever get here.
		else:
			raise TypeError(f"I don't know what to do with a {type(e)}")


	def run_lines(self, lines: list[str]):
		for l in lines:
			self.run(l, silent = True)
