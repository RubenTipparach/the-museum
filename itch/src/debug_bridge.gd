## Observed, never driven (CLAUDE.md 12): on the web build, window.ftDebug
## lets the playthrough read the state, where a thing is on screen and what a
## tap at a point would hit. It cannot move the game: the harness taps where
## a player taps. JS calls ftDebug.query(json) and reads window.ftDebugResult,
## because a callback made with JavaScriptBridge returns nothing to JS.
class_name DebugBridge
extends RefCounted

var game: Node
var _query_cb: JavaScriptObject


func _init(g: Node) -> void:
	game = g
	if not OS.has_feature("web"):
		return
	_query_cb = JavaScriptBridge.create_callback(_query)
	JavaScriptBridge.eval("window.ftDebug = {}; window.ftDebugResult = null;", true)
	var dbg: JavaScriptObject = JavaScriptBridge.get_interface("ftDebug")
	dbg.query = _query_cb


func _query(args: Array) -> void:
	var q = JSON.parse_string(String(args[0]))
	var result = answer(q if q is Dictionary else {})
	JavaScriptBridge.eval("window.ftDebugResult = " + JSON.stringify(result) + ";", true)


func answer(q: Dictionary) -> Variant:
	match q.get("op", ""):
		"state":
			return game.debug_state()
		"screenOf":
			return game.screen_of(String(q.get("kind", "")), q.get("i", null), String(q.get("id", "")))
		"hitAt":
			return Interaction.hits(game.rig.camera, Vector2(float(q["x"]), float(q["y"])), game.T)
		"hud":
			return game.hud.debug_rects()
		"lit":
			return game.lit_fraction()
		_:
			return {"error": "unknown op"}
