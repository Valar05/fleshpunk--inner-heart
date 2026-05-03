# Audio Pipeline

The TTS pipeline uses phrase-sized clips.
Do not generate isolated one-word files.

Use:

```sh
python tools/tts_manifest.py refresh
python tools/tts_manifest.py audit --fail-on-findings
python tools/tts_manifest.py plan
```

When ready to spend API calls:

```sh
OPENAI_API_KEY=... python tools/tts_manifest.py generate
```

The default generation target is:
- model: `gpt-4o-mini-tts`
- voice: `nova`
- format: `wav`
- output: `res://audio/tts/*.wav`

Each clip hash includes text, model, voice, instructions, and response format.
Unchanged clips are skipped when the output exists and the local cache matches.
