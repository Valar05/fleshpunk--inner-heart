extends SceneTree

const MANIFEST_PATH := "res://audio/tts_manifest.json"


func _init() -> void:
	if not FileAccess.file_exists(MANIFEST_PATH):
		push_error("Missing TTS manifest.")
		quit(1)
		return

	var file := FileAccess.open(MANIFEST_PATH, FileAccess.READ)
	if file == null:
		push_error("Could not open TTS manifest.")
		quit(1)
		return

	var parsed = JSON.parse_string(file.get_as_text())
	if not parsed is Dictionary:
		push_error("TTS manifest is not valid JSON.")
		quit(1)
		return

	var clips = parsed.get("clips", [])
	if not clips is Array:
		push_error("TTS manifest clips are missing.")
		quit(1)
		return

	var found := 0
	for clip in clips:
		if not clip is Dictionary:
			continue
		var clip_id := str(clip.get("id", ""))
		found += 1
		var clip_file := str(clip.get("file", ""))
		if not ResourceLoader.exists(clip_file) and not FileAccess.file_exists(clip_file):
			push_error("TTS clip is missing: %s" % clip_file)
			quit(1)
			return
		var stream = _load_audio_stream(clip_file)
		if not stream is AudioStream:
			push_error("TTS clip is not an AudioStream: %s" % clip_file)
			quit(1)
			return

	if found != clips.size():
		push_error("Expected %d TTS clips, found %d." % [clips.size(), found])
		quit(1)
		return

	quit(0)


func _load_audio_stream(clip_file: String) -> AudioStream:
	if ResourceLoader.exists(clip_file):
		var imported_stream = load(clip_file)
		if imported_stream is AudioStream:
			return imported_stream
	match clip_file.get_extension().to_lower():
		"wav":
			return AudioStreamWAV.load_from_file(clip_file)
		"mp3":
			return AudioStreamMP3.load_from_file(clip_file)
		"ogg":
			return AudioStreamOggVorbis.load_from_file(clip_file)
	return load(clip_file) as AudioStream
