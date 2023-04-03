from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import print_formatted_text as printf
from prompt_toolkit.shortcuts import clear as clear_screen
from prompt_toolkit import prompt

import os.path
from pyparsing import exceptions as ppx

import lamb_engine

commands = {}
help_texts = {}

def lamb_command(
		*,
		command_name = None,
		help_text: str
	):
	"""
	A decorator that allows us to easily make commands
	"""

	def inner(func):
		name = func.__name__ if command_name is None else command_name

		commands[name] = func
		help_texts[name] = help_text
	return inner

@lamb_command(
	command_name = "step",
	help_text = "Toggle step-by-step reduction"
)
def cmd_step(command, runner) -> None:
	if len(command.args) > 1:
		printf(
			HTML(
				f"<err>Command <code>:{command.name}</code> takes no more than one argument.</err>"
			),
			style = lamb_engine.utils.style
		)
		return

	target = not runner.step_reduction
	if len(command.args) == 1:
		if command.args[0].lower() in ("y", "yes"):
			target = True
		elif command.args[0].lower() in ("n", "no"):
			target = False
		else:
			printf(
				HTML(
					f"<err>Usage: <code>:step [yes|no]</code></err>"
				),
				style = lamb_engine.utils.style
			)
			return


	if target:
		printf(
			HTML(
				f"<warn>Enabled step-by-step reduction.</warn>"
			),
			style = lamb_engine.utils.style
		)
		runner.step_reduction = True
	else:
		printf(
			HTML(
				f"<warn>Disabled step-by-step reduction.</warn>"
			),
			style = lamb_engine.utils.style
		)
		runner.step_reduction = False

@lamb_command(
	command_name = "expand",
	help_text = "Toggle full expansion"
)
def cmd_expand(command, runner) -> None:
	if len(command.args) > 1:
		printf(
			HTML(
				f"<err>Command <code>:{command.name}</code> takes no more than one argument.</err>"
			),
			style = lamb_engine.utils.style
		)
		return

	target = not runner.full_expansion
	if len(command.args) == 1:
		if command.args[0].lower() in ("y", "yes"):
			target = True
		elif command.args[0].lower() in ("n", "no"):
			target = False
		else:
			printf(
				HTML(
					f"<err>Usage: <code>:expand [yes|no]</code></err>"
				),
				style = lamb_engine.utils.style
			)
			return


	if target:
		printf(
			HTML(
				f"<warn>Enabled complete expansion.</warn>"
			),
			style = lamb_engine.utils.style
		)
		runner.full_expansion = True
	else:
		printf(
			HTML(
				f"<warn>Disabled complete expansion.</warn>"
			),
			style = lamb_engine.utils.style
		)
		runner.full_expansion = False


@lamb_command(
	command_name = "save",
	help_text = "Save macros to a file"
)
def cmd_save(command, runner) -> None:
	if len(command.args) != 1:
		printf(
			HTML(
				f"<err>Command <code>:{command.name}</code> takes exactly one argument.</err>"
			),
			style = lamb_engine.utils.style
		)
		return

	target = command.args[0]
	if os.path.exists(target):
		confirm = prompt(
			message = FormattedText([
				("class:warn", "File exists. Overwrite? "),
				("class:text", "[yes/no]: ")
			]),
			style = lamb_engine.utils.style
		).lower()

		if confirm != "yes":
			printf(
				HTML(
					"<err>Cancelled.</err>"
				),
				style = lamb_engine.utils.style
			)
			return

	with open(target, "w") as f:
		f.write("\n".join(
			[f"{n} = {e.export()}" for n, e in runner.macro_table.items()]
		))

	printf(
		HTML(
			f"Wrote {len(runner.macro_table)} macros to <code>{target}</code>"
		),
		style = lamb_engine.utils.style
	)


@lamb_command(
	command_name = "load",
	help_text = "Load macros from a file"
)
def cmd_load(command, runner):
	if len(command.args) != 1:
		printf(
			HTML(
				f"<err>Command <code>:{command.name}</code> takes exactly one argument.</err>"
			),
			style = lamb_engine.utils.style
		)
		return

	target = command.args[0]
	if not os.path.exists(target):
		printf(
			HTML(
				f"<err>File {target} doesn't exist.</err>"
			),
			style = lamb_engine.utils.style
		)
		return

	with open(target, "r") as f:
		lines = [x.strip() for x in f.readlines()]

	for i in range(len(lines)):
		l = lines[i].strip()

		# Skip comments and empty lines
		if l.startswith("#"):
			continue
		if l == "":
			continue

		try:
			x = runner.parse(l)[0]
		except ppx.ParseException as e:
			printf(
				FormattedText([
					("class:warn", f"Syntax error on line {i+1:02}: "),
					("class:code", l[:e.loc]),
					("class:err", l[e.loc]),
					("class:code", l[e.loc+1:])
				]),
				style = lamb_engine.utils.style
			)
			return

		if not isinstance(x, lamb_engine.runner.runner.MacroDef):
			printf(
				FormattedText([
					("class:warn", f"Skipping line {i+1:02}: "),
					("class:code", l),
					("class:warn", f" is not a macro definition.")
				]),
				style = lamb_engine.utils.style
			)
			return

		runner.save_macro(x, silent = True)

		printf(
			FormattedText([
				("class:ok", f"Loaded {x.label}: ")
			] + lamb_engine.utils.lex_str(str(x.expr))),
			style = lamb_engine.utils.style
		)


@lamb_command(
	help_text = "Delete a macro"
)
def mdel(command, runner) -> None:
	if len(command.args) != 1:
		printf(
			HTML(
				f"<err>Command <code>:{command.name}</code> takes exactly one argument.</err>"
			),
			style = lamb_engine.utils.style
		)
		return

	target = command.args[0]
	if target not in runner.macro_table:
		printf(
			HTML(
				f"<warn>Macro \"{target}\" is not defined</warn>"
			),
			style = lamb_engine.utils.style
		)
		return

	del runner.macro_table[target]

@lamb_command(
	help_text = "Delete all macros"
)
def delmac(command, runner) -> None:
	confirm = prompt(
		message = FormattedText([
			("class:warn", "Are you sure? "),
			("class:text", "[yes/no]: ")
		]),
		style = lamb_engine.utils.style
	).lower()

	if confirm != "yes":
		printf(
			HTML(
				"<err>Cancelled.</err>"
			),
			style = lamb_engine.utils.style
		)
		return

	runner.macro_table = {}


@lamb_command(
	help_text = "Show macros"
)
def macros(command, runner) -> None:
	if len(runner.macro_table) == 0:
		printf(FormattedText([
				("class:warn", "No macros are defined."),
			]),
			style = lamb_engine.utils.style
		)
	else:
		printf(FormattedText([
				("class:cmd_h", "\nDefined Macros:\n"),
			] +
			[
				("class:text", f"\t{name} \t {exp}\n")
				for name, exp in runner.macro_table.items()
			]),
			style = lamb_engine.utils.style
		)

@lamb_command(
	help_text = "Clear the screen"
)
def clear(command, runner) -> None:
	clear_screen()
	lamb_engine.utils.show_greeting()

@lamb_command(
	help_text = "Get or set reduction limit"
)
def rlimit(command, runner) -> None:
	if len(command.args) == 0:
		if runner.reduction_limit is None:
			printf(
				HTML(
					"<ok>No reduction limit is set</ok>"
				),
				style = lamb_engine.utils.style
			)
		else:
			printf(
				HTML(
					f"<ok>Reduction limit is {runner.reduction_limit:,}</ok>"
				),
				style = lamb_engine.utils.style
			)
		return

	elif len(command.args) != 1:
		printf(
			HTML(
				f"<err>Command <code>:{command.name}</code> takes exactly one argument.</err>"
			),
			style = lamb_engine.utils.style
		)
		return

	t = command.args[0]
	if t.lower() == "none":
		runner.reduction_limit = None
		printf(
			HTML(
				f"<ok>Removed reduction limit</ok>"
			),
			style = lamb_engine.utils.style
		)
		return

	try:
		t = int(t)
	except ValueError:
		printf(
			HTML(
				"<err>Reduction limit must be a positive integer or \"none\".</err>"
			),
			style = lamb_engine.utils.style
		)
		return

	if 50 > t:
		printf(
			HTML(
				"<err>Reduction limit must be at least 50.</err>"
			),
			style = lamb_engine.utils.style
		)
		return

	runner.reduction_limit = t
	printf(
		HTML(
			f"<ok>Set reduction limit to {t:,}</ok>"
		),
		style = lamb_engine.utils.style
	)



@lamb_command(
	help_text = "Print this help"
)
def help(command, runner) -> None:
	printf(
		HTML(
			"\n<text>" +

			"<cmd_h>Usage:</cmd_h>" +
			"\n" +
			"\tWrite lambda expressions using your <cmd_key>\\</cmd_key> key." +
			"\n" +
			"\tMacros can be defined using <cmd_key>=</cmd_key>, as in <code>T = λab.a</code>" +
			"\n" +
			"\tRun commands using <cmd_key>:</cmd_key>, for example <code>:help</code>" +
			"\n" +
			"\tHistory can be accessed with <cmd_key>$</cmd_key>, which will expand to the result of the last successful reduction." +
			"\n\n" +
			"<cmd_h>Commands:</cmd_h>"+
			"\n" +
			"\n".join([
				f"\t<code>{name}</code> \t {text}"
				for name, text in help_texts.items()
			]) +
			"\n\n"
			"<muted>Detailed documentation can be found on this project's git page.</muted>" +
			"</text>"
		),
		style = lamb_engine.utils.style
	)