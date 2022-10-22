from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.shortcuts import clear as clear_screen

from runstatus import CommandStatus
import greeting



commands = {}
help_texts = {}

def lamb_command(*, help_text: str):
	def inner(func):
		commands[func.__name__] = func
		help_texts[func.__name__] = help_text
	return inner

def run(command, runner):
	return commands[command](runner)


@lamb_command(help_text = "Show macros")
def macros(runner):
	return CommandStatus(
		formatted_text = FormattedText([
			("#FF6600 bold", "\nDefined Macros:\n"),
		] +
		[
			("#FFFFFF", f"\t{name} \t {exp}\n")
			for name, exp in runner.macro_table.items()
		]
		)
	)

@lamb_command(help_text = "Clear the screen")
def clear(runner):
	clear_screen()
	greeting.show()


@lamb_command(help_text = "Print this help")
def help(runner):
	return CommandStatus(
		formatted_text = FormattedText([
			("#FF6600 bold", "\nUsage:\n"),
			(
				"#FFFFFF",
				"\tWrite lambda expressions using your "
			),
			(
				"#00FF00",
				"\\"
			),
			(
				"#FFFFFF",
				" key.\n" +
				"\tMacros can be defined using "
			),


			("#00FF00", "="),
			(
				"#FFFFFF",
				", as in "
			),
			(
				"#AAAAAA bold",
				"T = λab.a\n"
			),


			(
				"#FFFFFF",
				"\tRun commands using "
			),
			(
				"#00FF00",
				":"
			),
			(
				"#FFFFFF",
				", for example "
			),
			(
				"#AAAAAA bold",
				":help"
			),

			("#FF6600 bold", "\n\nCommands:\n")
		] +
		[
			("#FFFFFF", f"\t{name} \t {text}\n")
			for name, text in help_texts.items()
		]
		)
	)