if __name__ != "__main__":
	raise ImportError("lamb.__main__ should never be imported. Run it directly.")

from prompt_toolkit import PromptSession
from prompt_toolkit import print_formatted_text as printf
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import to_plain_text
from pyparsing import exceptions as ppx

import lamb


lamb.utils.show_greeting()


r = lamb.Runner(
	prompt_session = PromptSession(
		style = lamb.utils.style,
		lexer = lamb.utils.LambdaLexer(),
		key_bindings = lamb.utils.bindings
	),
	prompt_message = FormattedText([
		("class:prompt", "==> ")
	])
)

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
		]), style = lamb.utils.style)
		continue
	except lamb.node.ReductionError as e:
		printf(FormattedText([
			("class:err", f"{e.msg}\n")
		]), style = lamb.utils.style)
		continue

	printf("")
