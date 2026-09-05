## The four puzzles of the Elmorian exhibit, as plain state with no scene and
## no renderer, so tests/run_tests.gd can solve them headless (CLAUDE.md 4.3).
## This is the same rule set as mockups/elmorian-exhibit/puzzles.js, ported
## line for line; the two are kept in step by identical checks on both sides.
##
## Numbers here are the world's: six positions on a gaze dial, six pads and
## six word glyphs, because the Elmorians count in sixes (docs/WORLD.md 2).
class_name Puzzles
extends RefCounted

const WORDS := ["light", "stone", "eye", "touch", "door", "dark"]


## Where a dial position points: six marks round the disc, a sixth of a turn each.
static func pos_angle(k: int) -> float:
	return k * PI / 3.0

## Room 1: three eye discs, six positions each. The door wants all on 3; the
## final puzzle wants the sun, the far eye and the door.
class Gaze:
	var pos: Array[int] = [0, 5, 1]
	var door: Array[int] = [3, 3, 3]
	var final: Array[int] = [2, 4, 0]
	func tap(i: int) -> void:
		pos[i] = (pos[i] + 1) % 6
	func matches(target: Array[int]) -> bool:
		return pos[0] == target[0] and pos[1] == target[1] and pos[2] == target[2]

## Room 2: four rings on three pegs, Tower of Hanoi rules. Size 3 is largest.
class Stack:
	var pegs: Array = [[3, 2, 1, 0], [], []]
	var held: int = -1
	var from: int = -1
	var door_peg := 2
	var final_peg := 1
	## Returns "lift", "drop", "return", "refuse" or "empty".
	func tap(peg: int) -> String:
		var p: Array = pegs[peg]
		if held < 0:
			if p.is_empty():
				return "empty"
			held = p.pop_back()
			from = peg
			return "lift"
		if peg == from:
			p.push_back(held); held = -1; from = -1
			return "return"
		if not p.is_empty() and p[p.size() - 1] < held:
			return "refuse"
		p.push_back(held); held = -1; from = -1
		return "drop"
	func on(peg: int) -> bool:
		return held < 0 and (pegs[peg] as Array).size() == 4

## Room 3: six pads, a phrase is four in order. The greeting opens the door,
## the farewell is what the final puzzle wants, and they begin differently.
class Speech:
	var greeting: Array[int] = [0, 2, 3, 4]
	var farewell: Array[int] = [1, 5, 3, 2]
	var input: Array[int] = []
	var last: String = ""
	static func _is_prefix(inp: Array[int], phrase: Array[int]) -> bool:
		for i in inp.size():
			if inp[i] != phrase[i]:
				return false
		return true
	## Returns "ok", "greeting", "farewell" or "wrong".
	func tap(pad: int) -> String:
		input.append(pad)
		var g := _is_prefix(input, greeting)
		var f := _is_prefix(input, farewell)
		if not g and not f:
			input.clear()
			return "wrong"
		if g and input.size() == greeting.size():
			input.clear(); last = "greeting"; return "greeting"
		if f and input.size() == farewell.size():
			input.clear(); last = "farewell"; return "farewell"
		return "ok"
	func phrase(name: String) -> Array[int]:
		return greeting if name == "greeting" else farewell

## The exhibit: the three puzzles and which doors have opened. A door that has
## opened stays open, so a solved room can be re-entered for the final puzzle.
class Exhibit:
	var gaze := Gaze.new()
	var stack := Stack.new()
	var speech := Speech.new()
	var open: Array[bool] = [true, false, false, false, false]
	func final_matches() -> bool:
		return gaze.matches(gaze.final) and stack.on(stack.final_peg) and speech.last == "farewell"
	func refresh_doors() -> void:
		if gaze.matches(gaze.door): open[1] = true
		if stack.on(stack.door_peg): open[2] = true
		if speech.last != "": open[3] = true
		if final_matches(): open[4] = true
	## The save is the state that matters, nothing derived (ADR-2).
	func to_dict() -> Dictionary:
		return {"gaze": gaze.pos, "pegs": stack.pegs, "last": speech.last, "open": open}
	## JSON gives back floats and untyped arrays; the state is ints and bools.
	func from_dict(d: Dictionary) -> void:
		for i in 3:
			gaze.pos[i] = int(d.get("gaze", gaze.pos)[i])
		var pegs: Array = d.get("pegs", stack.pegs)
		stack.pegs = []
		for p in pegs:
			var q: Array = []
			for v in p:
				q.append(int(v))
			stack.pegs.append(q)
		speech.last = String(d.get("last", ""))
		for i in 5:
			open[i] = bool(d.get("open", open)[i])
