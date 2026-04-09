# SignBridge

Real-time ASL signing overlay for Telegram calls on Android.

The hearing person speaks normally. The deaf person sees a cartoon avatar signing everything said, rendered as a floating overlay on top of Telegram — with English subtitles always visible.

**Free. Open source. No account required.**

## How It Works

```
Hearing person speaks on Telegram
       ↓
SignBridge bot joins the call, captures audio
       ↓
Audio streams to phone over WebSocket
       ↓
Voice Activity Detection (on-device)
       ↓
Speech-to-Text (Vosk, on-device, free)
       ↓
ASL Translation (224 patterns → vector similarity → grammar rules)
       ↓
Sign Dictionary (115 signs + fingerspelling for unknown words)
       ↓
3D Avatar signs as floating overlay on top of Telegram
+ English subtitles + confidence indicator
```

## Status

**Alpha — builds, 42 tests pass, needs first real device test.**

| Component | Status |
|-----------|--------|
| Android app (Kotlin) | 25 source files, compiles clean |
| 3D renderer (OpenGL ES + LBS skinning) | Complete, needs artist GLB model |
| 2D sprite renderer (video call mode) | Complete |
| STT (Vosk, on-device) | Integrated |
| ASL translation (3-tier) | 224 patterns + 378 vectors + grammar rules |
| Sign dictionary | 115 signs (79 ASL + 26 fingerspelling + 10 numbers) |
| Bot relay server | Complete (FastAPI + pytgcalls) |
| Unit tests | 42 tests, all passing |

## Quick Start

### Build the APK

```bash
export ANDROID_HOME=/path/to/android-sdk
./gradlew assembleDebug
# → app/build/outputs/apk/debug/app-debug.apk
```

### Deploy the Relay Server

The relay bot is **required** — it joins Telegram calls and streams audio to the app.

```bash
cd relay
pip install -r requirements.txt

# Get credentials: https://my.telegram.org
export TELEGRAM_PHONE="+1234567890"
export TELEGRAM_APP_ID="12345"
export TELEGRAM_APP_HASH="abcdef"

uvicorn main:app --host 0.0.0.0 --port 8080
```

### Install and Run

1. Install APK on Android 10+ phone
2. Grant overlay + notification permissions
3. Download speech model (~50MB, one-time)
4. Enter relay server URL
5. Open Telegram, start a call
6. Tap "Start Overlay" in SignBridge

### Run Tests

```bash
./gradlew testDebugUnitTest   # 42 tests
```

## Audio Capture: Why a Relay Bot?

Android's AudioPlaybackCapture API **cannot capture voice call audio** — `USAGE_VOICE_COMMUNICATION` is hardcoded excluded at the OS level (confirmed from AOSP source). Telegram uses this audio type for all calls.

The relay bot (pytgcalls) is the only viable path. The hearing person will see the bot as a call participant.

## Architecture

```
signbridge/
├── app/                    # Android app (Kotlin)
│   └── src/main/java/com/signbridge/app/
│       ├── audio/          # RelayClient (WebSocket) + AudioCaptureService
│       ├── overlay/        # Floating overlay service
│       ├── renderer/       # OpenGL ES 3D + 2D sprite + GLTF loader
│       ├── stt/            # VAD + Vosk STT pipeline
│       ├── translation/    # 3-tier ASL translation + grammar rules
│       ├── model/          # Shared types (Quaternion, FaceParams, etc.)
│       └── ui/             # Setup, Main, Settings
├── relay/                  # Bot relay server (Python/FastAPI)
├── dictionary/             # Sign dictionary pipeline (Python)
├── agent4/                 # ASL translation engine (Python)
├── translation/            # Extended translation research
└── tools/                  # Avatar GLB generator, utilities
```

## Contributing

**See [NEXT_TASKS.md](NEXT_TASKS.md) for prioritized work items.**

### Adding Signs

```python
# In dictionary/build/common_signs_extended.py, add:
def sign_your_word() -> list[RawFrame]:
    """YOUR-WORD: Description of the sign."""
    return [
        _make_frame(0, _OPEN_HAND, rh_offset=(x, y, z)),
        _make_frame(400, _FIST, rh_offset=(x2, y2, z2)),
    ]

# Register in EXTENDED_SIGNS dict, rebuild dictionary
```

### Adding Translation Patterns

```json
// In app/src/main/assets/translation/patterns.json, add:
{"english": "i want {THING}", "asl": "{THING} I WANT", "category": "request"}
```

### Replacing the Avatar

1. Create GLB in Blender with 48 named joints (see `tools/generate_avatar_glb.py`)
2. Drop at `app/src/main/assets/models/avatar.glb`
3. No code changes needed — renderer loads it automatically

## Documentation

| Document | Content |
|----------|---------|
| [README.md](README.md) | This file — overview, quick start |
| [SPEC.md](SPEC.md) | Full product specification |
| [HANDOVER.md](HANDOVER.md) | Complete technical state — every file, every decision |
| [NEXT_TASKS.md](NEXT_TASKS.md) | Prioritized task list with effort estimates |
| [LICENSE](LICENSE) | Apache 2.0 |

## License

Apache 2.0
