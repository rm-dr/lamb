import PyInstaller.__main__

# Run this file to build a standalone executable.
# pyinstaller does not build cross-platform.

PyInstaller.__main__.run([
	"lamb/__main__.py",
	"--onefile",
	"--console"
])