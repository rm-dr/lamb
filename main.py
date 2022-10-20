from parser import Parser
import tokens
import colorama as cr


class lambda_runner:
	def __init__(self):
		self.macro_table = {}
		self.expr = None

	# Apply a list of definitions
	def run_names(self, lines):
		print("Added names:")
		for l in lines:
			if isinstance(l, str):
				e = Parser.parse_assign(l)
			else:
				e = l

			if e.label in self.macro_table:
				raise NameError(f"Label {e.label} exists!")

			e.exp.bind_variables()
			self.macro_table[e.label] = e.exp
			print(f"\t{e}")
		print("\n")

	def set_expr(self, expr: str | None = None):
		if expr == None:
			self.expr = None
			print("Removed expression.\n")
			return

		self.expr = Parser.parse_expression(expr)
		self.expr.bind_variables()
		print(f"Set expression to {self.expr}\n")

	def run(self):
		if isinstance(self.expr, tokens.lambda_apply):
			self.expr = self.expr.expand(self.macro_table)
		elif isinstance(self.expr, tokens.lambda_func):
			self.expr = self.expr.expand(self.macro_table)
		else:
			return None
		return self.expr



"""
   |  _.._ _.|_
   |_(_|| | ||_)
       1.1.0

       __  __
    ,-`  ``  `,
   (`   \      )
  (`     \     `)
  (,    / \    _)
   (`  /   \   )
    `'._.--._.'

 A λ calculus engine
"""

b = cr.Style.BRIGHT
v = cr.Fore.GREEN + cr.Style.BRIGHT
l = cr.Fore.RED + cr.Style.BRIGHT
n = cr.Style.RESET_ALL
t = cr.Fore.GREEN

print(f"""

{b}    |  _.._ _.|_
    |_(_|| | ||_){n}
        {v}1.1.0{n}
        __  __
     ,-`  ``  `,
    (`   {l}\{n}      )
   (`     {l}\{n}     `)
   (,    {l}/ \{n}    _)
    (`  {l}/   \{n}   )
     `'._.--._.'

{t} A λ calculus engine{n}

"""[1:-1])


r = lambda_runner()

r.run_names([
	"T = a -> b -> a",
	"F = a -> b -> a",
	"NOT = a -> (a F T)",
	"AND = a -> b -> (a F b)",
	"OR = a -> b -> (a T b)",
	"XOR = a -> b -> (a (NOT a b) b)"
])

r.run_names([
	"w = x -> (x x)",
	"W = (w w)",
	"Y = f -> ( (x -> (f (x x))) (x -> (f (x x))) )",
	#"l = if_true -> if_false -> which -> ( which if_true if_false )"
])

r.run_names([
	"inc = n -> f -> x -> (f (n f x))",
	"zero = a -> x -> x",
	"one = f -> x -> (f x)",
])

print("\n")

#AND = r.run()
#OR = r.run()
#XOR = r.run()

r.set_expr(
	"(" +
	"inc (inc (inc (zero)))"
	+ ")"
)

print(repr(r.expr))
print("")

outs = [str(r.expr)]
for i in range(300):
	x = r.run()
	s = str(x)
	p = s if len(s) < 100 else s[:97] + "..."

	if s in outs:
		print(p)
		print("\nLoop detected, exiting.")
		break

	if x is None:
		print("\nCannot evaluate any further.")
		break

	outs.append(s)
	print(p)

print(f"Performed {i} {'operations' if i != 1 else 'operation'}.")