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
	"T = λab.a",
	"F = λab.b",
	"NOT = λa.(a F T)",
	"AND = λab.(a F b)",
	"OR = λab.(a T b)",
	"XOR = λab.(a (NOT a b) b)",
	"w = λx.(x x)",
	"W = w w",
	"Y = λf.( (λx.(f (x x))) (λx.(f (x x))) )",
	"PAIR = λabi.( i a b )",
	"inc = λnfa.(f (n f a))",
	"zero = λax.x",
	"one = λfx.(f x)"
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
	except tokens.ReductionError as e:
		printf(FormattedText([
			("#FF0000", f"{e.msg}"),
			("#FFFFFF", "\n")
		]))
		continue

	# If this line defined a macro, print nothing.
	if isinstance(x, runner.MacroStatus):
		printf(FormattedText([
			("#FFFFFF", "Set "),
			("#FF00FF", x.macro_label),
			("#FFFFFF", " to "),
			("#FFFFFF", str(x.macro_expr))
		]))


	if isinstance(x, runner.CommandStatus):
		printf(x.formatted_text)

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
