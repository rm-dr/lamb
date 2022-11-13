# See makedemo.sh

#Output lambdemo.mp4
Output lambdemo.gif

Set FontSize 30
Set Width 2000
Set Height 1500
Set FontFamily "FantasqueSansMono NF"
Set TypingSpeed 60ms
Set Framerate 30

# Intro
Sleep 2000ms
Type "lamb"
Sleep 1000ms
Enter
Sleep 2000ms

# Demo 1: load
Type ":load ../macros.lamb"
Sleep 500ms
Enter
Sleep 2000ms

Type "NOT T"
Sleep 1000ms
Enter
Sleep 6s

Type ":clear"
Sleep 1000ms
Enter
Sleep 1500ms


# Demo 2: stepping
Type ":step"
Sleep 500ms
Enter
Sleep 1500ms

Type "NOT T"
Sleep 100ms
Enter
Sleep 1500ms
Enter
Sleep 760ms
Enter
Sleep 850ms
Enter
Sleep 650ms
Enter
Sleep 700ms
Enter

Sleep 3000ms

Type ":step"
Sleep 500ms
Enter
Sleep 6s
Type ":clear"
Sleep 1000ms
Enter
Sleep 1500ms

# Demo 3: macros
Type "M = \x.x x"
Sleep 500ms
Enter
Sleep 500ms

Type "M M"
Sleep 500ms
Enter
Sleep 3s
Ctrl+c
Sleep 1000ms

Type "Y FAC 3"
Sleep 500ms
Enter
Sleep 6s
