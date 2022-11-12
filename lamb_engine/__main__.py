from prompt_toolkit import PromptSession
from prompt_toolkit import print_formatted_text as printf
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import to_plain_text
from pyparsing import exceptions as ppx
import sys

import lamb_engine

def main():

	lamb_engine.utils.show_greeting()


	r = lamb_engine.Runner(
		prompt_session = PromptSession(
			style = lamb_engine.utils.style,
			lexer = lamb_engine.utils.LambdaLexer(),
			key_bindings = lamb_engine.utils.bindings
		),
		prompt_message = FormattedText([
			("class:prompt", "==> ")
		])
	)

	# Load files passed as arguments
	if len(sys.argv) > 1:
		for i in range(1, len(sys.argv)):
			try:
				printf(FormattedText([
					("class:warn", "\nLoading file "),
					("class:code", sys.argv[i]),
				]), style = lamb_engine.utils.style)
				r.run(":load " + sys.argv[i])
			except:
				printf(FormattedText([
					("class:err", "Error. Does this file exist?"),
				]), style = lamb_engine.utils.style)

		print("")

	while True:
		try:
			i = r.prompt()

		# Catch Ctrl-C and Ctrl-D
		except KeyboardInterrupt:
			printf("\n\nGoodbye.\n")
			break
		except EOFError:
			printf("\n\nGoodbye.\n")
			break

		# Skip empty lines
		if i.strip() == "":
			continue

		# Try to run an input line.
		# Catch parse errors and point them out.
		try:
			x = r.run(i)
		except ppx.ParseException as e:
			l = len(to_plain_text(r.prompt_session.message))
			printf(FormattedText([
				("class:err", " "*(e.loc + l) + "^\n"),
				("class:err", f"Syntax error at char {e.loc}."),
				("class:text", "\n")
			]), style = lamb_engine.utils.style)
			continue
		except lamb_engine.nodes.ReductionError as e:
			printf(FormattedText([
				("class:err", f"{e.msg}\n")
			]), style = lamb_engine.utils.style)
			continue

		printf("")

if __name__ == "__main__":
	main()
