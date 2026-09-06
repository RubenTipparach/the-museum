## The HUD: the room's name, the label card, Read and Back, the room chips,
## the hint and the toast. It shows what main.gd tells it and reports what was
## pressed; it decides nothing. Every panel is a fixed, authored size, and the
## card's text scrolls rather than pushing (CLAUDE.md 9).
class_name Hud
extends CanvasLayer

signal close_pressed
signal read_pressed
signal back_pressed
signal restart_pressed
signal about_pressed
signal chip_pressed(room: int)

@onready var sub: Label = $Root/Top/Sub
@onready var room_name: Label = $Root/Top/Name
@onready var restart: Button = $Root/Restart
@onready var about: Button = $Root/About
@onready var card: PanelContainer = $Root/Card
@onready var card_title: Label = $Root/Card/VBox/Head/Title
@onready var card_close: Button = $Root/Card/VBox/Close
@onready var card_scroll: ScrollContainer = $Root/Card/VBox/Scroll
@onready var card_text: RichTextLabel = $Root/Card/VBox/Scroll/Text
@onready var read: Button = $Root/Read
@onready var back: Button = $Root/Tools/Back
@onready var chips: HBoxContainer = $Root/Chips
@onready var hint: Label = $Root/Hint
@onready var toast_label: Label = $Root/Toast

var _chip_here: StyleBox
var _chip_plain: StyleBox
var _toast_tween: Tween


func _ready() -> void:
	card_close.pressed.connect(func() -> void: close_pressed.emit())
	read.pressed.connect(func() -> void: read_pressed.emit())
	back.pressed.connect(func() -> void: back_pressed.emit())
	restart.pressed.connect(func() -> void: restart_pressed.emit())
	about.pressed.connect(func() -> void: about_pressed.emit())
	_chip_here = chips.get_node("chip_0").get_theme_stylebox("pressed")
	_chip_plain = chips.get_node("chip_0").get_theme_stylebox("normal")
	for i in 6:
		var b: Button = chips.get_node("chip_%d" % i)
		var art := "word_4" if i == 0 else ("word_5" if i == 5 else "numeral_%d" % i)
		b.icon = MaterialLibrary.art_texture(art)
		b.pressed.connect(func() -> void: chip_pressed.emit(i))
	card.visible = false
	read.visible = false
	back.visible = false
	toast_label.modulate.a = 0.0


func set_room(sub_text: String, name_text: String, names: Array) -> void:
	sub.text = sub_text
	room_name.text = name_text
	for i in 6:
		chips.get_node("chip_%d" % i).tooltip_text = names[i]


func show_card(title: String, text: String) -> void:
	card_title.text = title
	card_text.text = text
	card.visible = true
	read.visible = false
	card_scroll.scroll_vertical = 0


func hide_card() -> void:
	card.visible = false


func card_visible() -> bool:
	return card.visible


func set_tools(read_visible: bool, back_visible: bool) -> void:
	read.visible = read_visible
	back.visible = back_visible


## Back and Read share the bottom band with the room chips, and at 390 px they
## do not all fit; while an object is being looked at the chips go.
func set_inspecting(on: bool) -> void:
	chips.visible = not on


func set_chips(here: int, reachable: Array) -> void:
	for i in 6:
		var b: Button = chips.get_node("chip_%d" % i)
		b.add_theme_stylebox_override("normal", _chip_here if i == here else _chip_plain)
		b.modulate.a = 1.0 if reachable[i] else 0.35


func toast(text: String, seconds: float) -> void:
	toast_label.text = text
	if _toast_tween:
		_toast_tween.kill()
	toast_label.modulate.a = 1.0
	_toast_tween = create_tween()
	_toast_tween.tween_interval(seconds)
	_toast_tween.tween_property(toast_label, "modulate:a", 0.0, 0.5)


func hint_gone() -> void:
	if hint.visible:
		var tw := create_tween()
		tw.tween_property(hint, "modulate:a", 0.0, 0.8)
		tw.tween_callback(func() -> void: hint.visible = false)


func restart_armed(on: bool) -> void:
	restart.text = "tap again to restart" if on else "restart"


## Where each control is, in window pixels, for the playthrough: the HUD is
## drawn in the canvas, so a harness cannot find a button by its text.
func debug_rects() -> Dictionary:
	var out := {}
	var named := {"restart": restart, "about": about, "close": card_close, "read": read, "back": back}
	for i in 6:
		named["chip_%d" % i] = chips.get_node("chip_%d" % i)
	for k in named:
		var c: Control = named[k]
		var xf: Transform2D = get_viewport().get_final_transform() * c.get_global_transform_with_canvas()
		var o := xf * Vector2.ZERO
		var sz := xf.basis_xform(c.size)
		out[k] = {"x": o.x, "y": o.y, "w": sz.x, "h": sz.y, "visible": c.is_visible_in_tree(), "text": c.text if c is Button else ""}
	return out
