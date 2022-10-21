from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import to_plain_text
from prompt_toolkit.key_binding import KeyBindings

from pyparsing import exceptions as ppx

from parser import Parser
from runner import Runner
import tokens
import greeting


# Replace "\" with a pretty "λ" in the prompt
bindings = KeyBindings()
@bindings.add("\\")
def _(event):
	event.current_buffer.insert_text("λ")

session = PromptSession(
	message = FormattedText([
		("#00FFFF", "~~> ")
	]),
	key_bindings = bindings
)


greeting.show()




r = Runner()

r.run_lines([
	"T = λa.λb.a",
	"F = λa.λb.b",
	"NOT = \\a.(a F T)",
	#"AND = a -> b -> (a F b)",
	#"OR = a -> b -> (a T b)",
	#"XOR = a -> b -> (a (NOT a b) b)",
	#"w = x -> (x x)",
	#"W = (w w)",
	#"Y = f -> ( (x -> (f (x x))) (x -> (f (x x))) )",
	#"l = if_true -> if_false -> which -> ( which if_true if_false )"
	#"inc = n -> f -> x -> (f (n f x))",
	#"zero = a -> x -> x",
	#"one = f -> x -> (f x)",
])


while True:
	try:
		i = session.prompt()

	# Catch Ctrl-C and Ctrl-D
	except KeyboardInterrupt:
		print("")
		break
	except EOFError:
		print("")
		break

	if i.strip() == "":
		continue


	try:
		x = r.run(i)
	except ppx.ParseException as e:
		l = len(to_plain_text(session.message))
		print_formatted_text(FormattedText([
			("#FF0000", " "*(e.loc + l) + "^\n"),
			("#FF0000", f"Syntax error at char {e.loc}."),
			("#FFFFFF", "\n")
		]))
		continue


	print_formatted_text(FormattedText([
		("#00FF00", "    = "),
		("#FFFFFF", str(x))
	]))

	print("")
