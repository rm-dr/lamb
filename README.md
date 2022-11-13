# Lamb: A Lambda Calculus Engine

If you're reading this on PyPi, go [here](https://git.betalupi.com/Mark/lamb).

![Lamb demo](https://betalupi.com/static/git/lambdemo.gif)


## Installation

### Method 1: [PyPi](https://pypi.org/project/lamb-engine)
1. *(Optional but recommended)* make and enter a [venv](https://docs.python.org/3/library/venv.html).
2. `pip install lamb-engine`
3. `lamb`

### Method 2: Git
1. Clone this repository.
2. Make and enter a [virtual environment](https://docs.python.org/3/library/venv.html).
3. ``cd`` into this directory
4. Run ``pip install .``
5. Run ``lamb``

-------------------------------------------------

## Usage


Type lambda expressions into the prompt, and Lamb will evaluate them. \
Use your `\` (backslash) key to type a `λ`. \
To define macros, use `=`. For example,
```
==> T = λab.a
==> F = λab.a
==> NOT = λa.a F T
```

Note that there are spaces in `λa.a F T`. With no spaces, `aFT` will be parsed as one variable. \
Lambda functions can only take single-letter, lowercase arguments. `λA.A` is not valid syntax. \
Free variables will be shown with a `'`, like `a'`.

Macros are case-sensitive. If you define a macro `MAC` and accidentally write `mac` in the prompt, `mac` will become a free variable.

Numbers will automatically be converted to Church numerals. For example, the following line will reduce to `T`.
```
==> 3 NOT F
```

If an expression takes too long to evaluate, you may interrupt reduction with `Ctrl-C`. \
Exit the prompt with `Ctrl-C` or `Ctrl-D`.

There are many useful macros in [macros.lamb](./macros.lamb). Download the file, then load them with the `:load` command:
```
==> :load macros.lamb
```

You can also pass files to lamb directly to have them loaded at startup:
```
lamb file1 file2
```

Use your up/down arrows to recall history.

Have fun!

-------------------------------------------------

## Commands

Lamb understands many commands. Prefix them with a `:` in the prompt.

`:help` Print a help message

`:clear` Clear the screen

`:rlimit [int | None]` Set maximum reduction limit. `:rlimit none` sets no limit.

`:macros` List macros.

`:mdel [macro]` Delete a macro

`:delmac` Delete all macros

`:step [yes | no]` Enable or disable step-by-step reduction. Toggle if no argument is given. When reducing by steps, the prompt tells you what kind of reduction was done last:

 - `M`: Macro expansion
 - `C`: Church expansion
 - `H`: History expansion
 - `F`: Function application

`:expand [yes | no]` Enable or disable full expansion. Toggle if no argument is given. If full expansion is enabled, ALL macros will be expanded when printing output.

`:save [filename]` \
`:load [filename]` \
Save or load macros from a file.
The lines in a file look exactly the same as regular entries in the prompt, but can only contain macro definitions. See [macros.lamb](./macros.lamb) for an example.

-------------------------------------------------

## Todo:
 - Prevent macro-chaining recursion
 - Cleanup warnings
 - Truncate long expressions in warnings
 - Loop detection
 - α-equivalence check
 - Unchurch command: make church numerals human-readable
 - Better Syntax highlighting
 - Complete file names and commands
 - Tests