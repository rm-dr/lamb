from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import print_formatted_text as printf
from prompt_toolkit.shortcuts import clear as clear_screen

import os.path
from pyparsing import exceptions as ppx

import lamb

commands = {}
help_texts = {}

def lamb_command(
		*,
		command_name: str | None = None,
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
	command_name = "save",
	help_text = "Save macros to a file"
)
def cmd_save(command, runner) -> None:
	if len(command.args) != 1:
		printf(
			HTML(
				"<err>Command <cmd_code>:{command.name}</cmd_code> takes exactly one argument.</err>"
			),
			style = lamb.utils.style
		)
		return

	target = command.args[0]
	if os.path.exists(target):
		confirm = runner.prompt_session.prompt(
			message = FormattedText([
				("class:warn", "File exists. Overwrite? "),
				("class:text", "[yes/no]: ")
			])
		).lower()

		if confirm != "yes":
			printf(
				HTML(
					"<err>Cancelled.</err>"
				),
				style = lamb.utils.style
			)
			return

	with open(target, "w") as f:
		f.write("\n".join(
			[f"{n} = {e}" for n, e in runner.macro_table.items()]
		))

	printf(
		HTML(
			f"Wrote {len(runner.macro_table)} macros to <cmd_code>{target}</cmd_code>"
		),
		style = lamb.utils.style
	)


@lamb_command(
	command_name = "load",
	help_text = "Load macros from a file"
)
def cmd_load(command, runner):
	if len(command.args) != 1:
		printf(
			HTML(
				"<err>Command <cmd_code>:{command.name}</cmd_code> takes exactly one argument.</err>"
			),
			style = lamb.utils.style
		)
		return

	target = command.args[0]
	if not os.path.exists(target):
		printf(
			HTML(
				f"<err>File {target} doesn't exist.</err>"
			),
			style = lamb.utils.style
		)
		return

	with open(target, "r") as f:
		lines = [x.strip() for x in f.readlines()]

	for i in range(len(lines)):
		l = lines[i]
		try:
			x = runner.parse(l)
		except ppx.ParseException as e:
			printf(
				FormattedText([
					("class:warn", f"Syntax error on line {i+1:02}: "),
					("class:cmd_code", l[:e.loc]),
					("class:err", l[e.loc]),
					("class:cmd_code", l[e.loc+1:])
				]),
				style = lamb.utils.style
			)
			return

		if not isinstance(x, lamb.runner.MacroDef):
			printf(
				FormattedText([
					("class:warn", f"Skipping line {i+1:02}: "),
					("class:cmd_code", l),
					("class:warn", f" is not a macro definition.")
				]),
				style = lamb.utils.style
			)
			return

		runner.save_macro(x, silent = True)

		printf(
			FormattedText([
				("class:ok", f"Loaded {x.label}: "),
				("class:cmd_code", str(x.expr))
			]),
			style = lamb.utils.style
		)


@lamb_command(
	help_text = "Delete a macro"
)
def mdel(command, runner) -> None:
	if len(command.args) != 1:
		printf(
			HTML(
				"<err>Command <cmd_code>:{command.name}</cmd_code> takes exactly one argument.</err>"
			),
			style = lamb.utils.style
		)
		return

	target = command.args[0]
	if target not in runner.macro_table:
		printf(
			HTML(
				f"<warn>Macro \"{target}\" is not defined</warn>"
			),
			style = lamb.utils.style
		)
		return

	del runner.macro_table[target]


@lamb_command(
	help_text = "Show macros"
)
def macros(command, runner) -> None:
	printf(FormattedText([
			("class:cmd_h", "\nDefined Macros:\n"),
		] +
		[
			("class:cmd_text", f"\t{name} \t {exp}\n")
			for name, exp in runner.macro_table.items()
		]),
		style = lamb.utils.style
	)

@lamb_command(
	help_text = "Clear the screen"
)
def clear(command, runner) -> None:
	clear_screen()
	lamb.utils.show_greeting()


@lamb_command(
	help_text = "Print this help"
)
def help(command, runner) -> None:
	printf(
		HTML(
			"\n<cmd_text>" +
			"<cmd_h>Usage:</cmd_h>" +
			"\n" +
			"\tWrite lambda expressions using your <cmd_key>\\</cmd_key> key." +
			"\n" +
			"\tMacros can be defined using <cmd_key>=</cmd_key>, as in <cmd_code>T = λab.a</cmd_code>" +
			"\n" +
			"\tRun commands using <cmd_key>:</cmd_key>, for example <cmd_code>:help</cmd_code>" +
			"\n\n" +
			"<cmd_h>Commands:</cmd_h>"+
			"\n" +
			"\n".join([
				f"\t<cmd_code>{name}</cmd_code> \t {text}"
				for name, text in help_texts.items()
			]) +
			"</cmd_text>"
		),
		style = lamb.utils.style
	)