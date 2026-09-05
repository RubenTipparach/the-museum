## Plays the sounds tools/gen_sfx.py made and the music tools/strudel rendered
## (ADR-12). The one place an audio path is spelled. Effects rotate through a
## few players so a quick pair of taps does not cut the first one off.
class_name AudioBank
extends Node

const SFX := "res://assets/audio/sfx/%s.wav"

@onready var players: Array[AudioStreamPlayer] = [$Sfx0, $Sfx1, $Sfx2, $Sfx3]
@onready var music: AudioStreamPlayer = $Music
@onready var tone: AudioStreamPlayer = $Tone

var _streams: Dictionary = {}
var _next := 0
var _started := false


func play(name: String) -> void:
	if not _streams.has(name):
		_streams[name] = load(SFX % name)
	var p := players[_next]
	_next = (_next + 1) % players.size()
	p.stream = _streams[name]
	p.play()


## The bed and the music start on the first touch, because a browser will
## not play a sound nobody asked for.
func wake() -> void:
	if _started:
		return
	_started = true
	if not tone.playing:
		tone.play()
	if not music.playing:
		music.play()
