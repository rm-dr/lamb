import tokens
from parser import Parser

class Runner:
	def __init__(self):
		self.macro_table = {}
		self.expr = None

	def exec_command(self, command: str):
		if command == "help":
			print("This is a help message.")

	# Apply a list of definitions
	def run(self, line: str):
		e = Parser.parse_line(line)

		if isinstance(e, tokens.macro_expression):
			if e.label in self.macro_table:
				raise NameError(f"Label {e.label} exists!")
			e.exp.bind_variables()
			self.macro_table[e.label] = e.exp

		elif isinstance(e, tokens.command):
			self.exec_command(e.name)
		else:
			e.bind_variables()
			self.expr = e

			outs = [str(e)]
			for i in range(300):
				r = self.expr.reduce(self.macro_table)
				self.expr = r.output
				s = str(r.output)
				p = s if len(s) < 100 else s[:97] + "..."

				#if s in outs:
					#print(p)
					#print("\nLoop detected, exiting.")
					#break

				if not r.was_reduced:
					print("\nCannot evaluate any further.")
					break

			print(f"Performed {i} {'operations' if i != 1 else 'operation'}.")
			return self.expr

	def run_lines(self, lines):
		for l in lines:
			self.run(l)
