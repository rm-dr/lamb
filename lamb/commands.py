from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import clear as clear_screen

from lamb.runstatus import CommandStatus
import lamb.utils as utils



commands = {}
help_texts = {}

def lamb_command(*, help_text: str):
	def inner(func):
		commands[func.__name__] = func
		help_texts[func.__name__] = help_text
	return inner

def run(command, runner):
	if command.name not in commands:
		return CommandStatus(
			formatted_text = FormattedText([
				("class:warn", f"Unknown command \"{command.name}\"")
			])
		)
	else:
		return commands[command.name](command, runner)

@lamb_command(help_text = "Delete a macro")
def mdel(command, runner):
	if len(command.args) != 1:
		return CommandStatus(
			formatted_text = HTML(
				"<warn>Command <cmd_code>:mdel</cmd_code> takes exactly one argument.</warn>"
			)
		)

	target = command.args[0]
	if target not in runner.macro_table:
		return CommandStatus(
			formatted_text = HTML(
				f"<warn>Macro \"{target}\" is not defined</warn>"
			)
		)

	del runner.macro_table[target]

@lamb_command(help_text = "Show macros")
def macros(command, runner):
	return CommandStatus(

		# Can't use HTML here, certain characters might break it.
		formatted_text = FormattedText([
			("class:cmd_h", "\nDefined Macros:\n"),
		] +
		[
			("class:cmd_text", f"\t{name} \t {exp}\n")
			for name, exp in runner.macro_table.items()
		]
		)
	)

@lamb_command(help_text = "Clear the screen")
def clear(command, runner):
	clear_screen()
	utils.show_greeting()


@lamb_command(help_text = "Print this help")
def help(command, runner):
	return CommandStatus(
		formatted_text = HTML(
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
				f"\t{name} \t {text}"
				for name, text in help_texts.items()
			]) +
			"</cmd_text>"
		)
	)