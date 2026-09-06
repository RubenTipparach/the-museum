## Headless checks: `godot --headless --path itch --script res://tests/run_tests.gd`.
## Solves every puzzle without a scene, the same twenty checks the JavaScript
## prototype's test.mjs makes, so the two rule sets cannot drift apart
## unnoticed. Prints ALL TESTS PASSED, or the first failure, and exits.
extends SceneTree

var _n := 0

func ok(cond: bool, msg: String) -> void:
	if not cond:
		printerr("FAIL: " + msg)
		quit(1)
		return
	_n += 1
	print("  ok  " + msg)

func hanoi(s: Puzzles.Stack, k: int, from: int, to: int, via: int) -> void:
	if k == 0: return
	hanoi(s, k - 1, from, via, to)
	assert(s.tap(from) == "lift"); assert(s.tap(to) == "drop")
	hanoi(s, k - 1, via, to, from)

func _init() -> void:
	var x := Puzzles.Exhibit.new()
	# Room 1
	ok(not x.gaze.matches(x.gaze.door), "gaze starts unsolved")
	for i in 3:
		while x.gaze.pos[i] != 3: x.gaze.tap(i)
	x.refresh_doors()
	ok(x.open[1] and not x.open[2], "gaze on the door opens door 1 only")
	for i in 6: x.gaze.tap(0)
	ok(x.gaze.pos[0] == 3, "six taps is a full turn")
	ok(x.open[1], "a door that opened stays open when the dials move")
	# Room 2
	var s := x.stack
	ok(s.tap(1) == "empty", "nothing to lift from an empty peg")
	ok(s.tap(0) == "lift" and s.held == 0, "lift the smallest")
	ok(s.tap(0) == "return" and s.held == -1, "tapping the same peg puts it back")
	s.tap(0); s.tap(2)
	s.tap(0)
	ok(s.tap(2) == "refuse" and s.held == 1, "a larger ring is refused and stays held")
	ok(s.tap(1) == "drop", "and goes on an empty peg")
	s.tap(1); s.tap(0); s.tap(2); s.tap(0)
	ok((s.pegs[0] as Array).size() == 4, "reset to the start")
	hanoi(s, 4, 0, 2, 1)
	x.refresh_doors()
	ok(s.on(2) and x.open[2], "four rings under the sun opens door 2")
	# Room 3
	var sp := x.speech
	ok(sp.tap(0) == "ok" and sp.tap(5) == "wrong" and sp.input.is_empty(), "a wrong pad resets")
	ok(sp.tap(3) == "wrong", "the third word cannot start either phrase")
	for p in [0, 2, 3]: assert(sp.tap(p) == "ok")
	ok(sp.tap(4) == "greeting" and sp.last == "greeting", "the greeting completes")
	x.refresh_doors()
	ok(x.open[3] and not x.open[4], "door 3 opens, the final door does not")
	# Room 4
	x.gaze.pos.assign([3, 3, 3])
	for i in 3:
		while x.gaze.pos[i] != x.gaze.final[i]: x.gaze.tap(i)
	x.refresh_doors()
	ok(not x.open[4], "the eyes alone are not enough")
	hanoi(s, 4, 2, 1, 0)
	x.refresh_doors()
	ok(not x.open[4], "the stack under the night eye is not enough either")
	for p in [1, 5, 3]: assert(sp.tap(p) == "ok")
	ok(sp.tap(2) == "farewell", "the farewell completes")
	x.refresh_doors()
	ok(x.open[4], "all three together open the final door")
	ok(x.open.all(func(b): return b), "every door in the exhibit is open")
	# The save round trips
	var y := Puzzles.Exhibit.new()
	y.from_dict(x.to_dict())
	ok(y.gaze.pos == x.gaze.pos and y.speech.last == "farewell" and y.open[4], "a save restores the exhibit")
	print("ALL %d CHECKS PASSED" % _n)
	quit(0)
