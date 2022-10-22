from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import print_formatted_text as printf
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import to_plain_text
from prompt_toolkit.key_binding import KeyBindings

from pyparsing import exceptions as ppx

from parser import Parser
import runner
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


printf("\n")
greeting.show()




r = runner.Runner()

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
		l = len(to_plain_text(session.message))
		printf(FormattedText([
			("#FF0000", " "*(e.loc + l) + "^\n"),
			("#FF0000", f"Syntax error at char {e.loc}."),
			("#FFFFFF", "\n")
		]))
		continue

	# If this line defined a macro, print nothing.
	if isinstance(x, runner.MacroStatus):
		pass

	# If this line was an expression, print reduction status
	elif isinstance(x, runner.ReduceStatus):
		printf(FormattedText([

			("#00FF00 bold", f"\nExit reason: "),
			x.stop_reason.value,

			("#00FF00 bold", f"\nReduction count: "),
			("#FFFFFF", str(x.reduction_count)),


			("#00FF00 bold", "\n\n    => "),
			("#FFFFFF", str(x.result)),
		]))

	print("")
