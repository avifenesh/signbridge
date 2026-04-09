# SignBridge — Handover Document

Last updated: 2026-04-09

## What Is This

An open source Android app that renders a real-time ASL (American Sign Language) avatar
overlay during Telegram voice/video calls. The hearing person speaks normally on Telegram.
The deaf person sees a cartoon avatar signing everything said, with English subtitles
for cross-referencing.

Free for everyone. Apache 2.0 license. No account required.

---

## Current State: Alpha — Builds, Tests Pass, Needs Device Testing

The app compiles, all 42 unit tests pass, and the APK is 108MB (debug).
No one has run it on a real phone yet. That is the single most important next step.

---

## Architecture (Confirmed)

```
[Telegram Call]
      |
[SignBridge Bot] ──joins call via pytgcalls, captures audio──> [Relay Server]
      |                                                              |
      |                                                    WebSocket (raw PCM)
      |                                                              |
      |                                                     [Android Phone]
      |                                                              |
      |                                            ┌─────────────────┼──────────────────┐
      |                                            |                 |                  |
      |                                      [Silero VAD]     [Vosk STT]        [ASL Translation]
      |                                      (speech detect)  (on-device)       (3-tier engine)
      |                                                              |                  |
      |                                                        English text        ASL gloss
      |                                                              |                  |
      |                                                        [Subtitle bar]    [Sign Dictionary]
      |                                                                                 |
      |                                                                          [Avatar Renderer]
      |                                                                          (OpenGL ES overlay)
      |                                                                                 |
      |                                                                    [Floating overlay on Telegram]
```

### Why Not On-Device Audio Capture?

**AudioPlaybackCapture (Path A) is dead.** Confirmed from AOSP source code:
- Android only allows capture of `USAGE_MEDIA`, `USAGE_GAME`, `USAGE_UNKNOWN`
- `USAGE_VOICE_COMMUNICATION` is **hardcoded excluded** at the OS audio policy level
- Telegram uses `USAGE_VOICE_COMMUNICATION` for all calls
- No app-level workaround exists

The bot relay (Path B) is the only viable path. The hearing person sees the bot
as a participant in the call. Path A code remains for potential future use.

---

## What's Built

### Android App (Kotlin) — `app/`

| File | Purpose | Status |
|------|---------|--------|
| `SignBridgeApp.kt` | Application class, notification channels | Done |
| `audio/AudioCaptureService.kt` | Path A audio capture (kept for future) | Done |
| `audio/RelayClient.kt` | Path B WebSocket client for relay server | Done |
| `overlay/OverlayService.kt` | Main overlay: avatar + subtitle + confidence + quick phrases | Done |
| `renderer/AvatarRenderer.kt` | OpenGL ES 2.0 skinned mesh renderer, LBS, confidence glow | Done |
| `renderer/ShaderProgram.kt` | GLSL shader compiler/linker | Done |
| `renderer/GltfModel.kt` | In-memory skinned mesh, GPU upload, pose application | Done |
| `renderer/GltfLoader.kt` | GLB parser (positions, normals, joints, weights, skin) | Done |
| `renderer/SpriteAvatarRenderer.kt` | 2D Canvas renderer for video call mode | Done |
| `stt/VadProcessor.kt` | Voice activity detection (energy-based, Silero VAD upgrade planned) | Done |
| `stt/VoskSttEngine.kt` | On-device STT via Vosk | Done |
| `stt/SttPipeline.kt` | Orchestrator: audio → VAD → STT → translation → signs | Done |
| `translation/AslTranslationEngine.kt` | 3-tier cascade: pattern hash → vector similarity → grammar rules | Done |
| `translation/PatternHashTable (in above)` | Tier 1: 224 template patterns with {SLOT} extraction | Done |
| `translation/VectorSimilarityIndex.kt` | Tier 2: 378 pre-embedded patterns, cosine similarity | Done |
| `translation/AslGrammarRules.kt` | Fallback: rule-based ASL grammar transforms | Done |
| `translation/SignDictionary.kt` | Loads quaternion keyframes, fingerspelling, transitions | Done |
| `model/SignModels.kt` | All shared types: Quaternion (slerp), FaceParams (lerp), SignEntry, etc. | Done |
| `ui/MainActivity.kt` | Home screen, start overlay, relay status | Done |
| `ui/SetupActivity.kt` | First launch: permissions, model download, relay URL | Done |
| `settings/SettingsActivity.kt` | STT provider, avatar size, captions, battery saver | Done |
| `util/Preferences.kt` | SharedPreferences wrapper, all settings | Done |

**GLSL Shaders** (`assets/shaders/`):
- `avatar_vert.glsl` — Vertex shader with linear blend skinning (48 bones, 4 influences)
- `avatar_frag.glsl` — Fragment shader with diffuse lighting + fresnel confidence glow

**Assets:**
- `models/avatar.glb` — 17KB procedural placeholder (48 joints, 187 verts)
- `dictionary/signs.json` — 115 signs in quaternion keyframe format
- `translation/patterns.json` — 224 ASL translation patterns
- `translation/vector_index.json` — 378 pre-embedded pattern vectors (752KB)

### Relay Server (Python) — `relay/`

| File | Purpose | Status |
|------|---------|--------|
| `main.py` | FastAPI + WebSocket server | Done |
| `bridge.py` | pytgcalls integration, joins Telegram calls | Done |
| `session.py` | Session state machine (JOINING→ACTIVE→LEAVING→CLOSED) | Done |
| `config.py` | Environment-based configuration | Done |

### ASL Translation Engine (Python) — `agent4/`

| File | Purpose | Status |
|------|---------|--------|
| `asl_engine/engine.py` | 3-tier cascade orchestrator | Done |
| `asl_engine/tier1.py` | Pattern hash with regex slots | Done |
| `asl_engine/tier2.py` | Vector similarity + BoW embedder | Done |
| `asl_engine/tier3.py` | T5-small stub (not trained) | Stub |
| `asl_engine/embedder_minilm.py` | MiniLM-L6-v2 ONNX embedder | Done |
| `asl_engine/dictionary.py` | Gloss → sign metadata lookup | Done |
| `asl_engine/fingerspell.py` | Fallback fingerspelling | Done |
| `asl_engine/normalize.py` | Text normalization, contractions | Done |
| `data/patterns.json` | 224 patterns | Done |
| `data/dictionary.json` | Gloss → sign ID mapping | Done |
| `scripts/download_models.py` | MiniLM model download | Done |
| `scripts/build_index.py` | Pre-embed patterns | Done |

### Sign Dictionary Pipeline (Python) — `dictionary/`

| File | Purpose | Status |
|------|---------|--------|
| `extract/mediapipe.py` | Video → hand/body/face landmarks | Done |
| `extract/normalize.py` | Coordinate normalization | Done |
| `keyframes/select.py` | Velocity-based keyframe selection | Done |
| `keyframes/transitions.py` | Transition interpolation | Done |
| `build/builder.py` | Dictionary assembler | Done |
| `build/fingerspelling.py` | 26 hand-authored A-Z poses | Done |
| `build/numbers.py` | 10 hand-authored 0-9 poses | Done |
| `build/common_signs.py` | 33 common ASL signs | Done |
| `build/common_signs_extended.py` | 46 more common signs | Done |
| `build/convert_for_app.py` | Position→quaternion IK converter | Done |
| `validate/quality.py` | Automated quality checks | Done |

### Extended Translation Research — `translation/`

| File | Purpose | Status |
|------|---------|--------|
| `tier1/patterns.py` | 1200+ lines of pattern definitions | Done |
| `tier2/similarity.py` | FAISS-based vector search | Done |
| `tier3/train.py` | T5-small fine-tuning infrastructure | Framework only |
| `gloss/rules.py` | ASL grammar rules (ported to Kotlin) | Done |

### Tests — `app/src/test/`

| File | Tests | Status |
|------|-------|--------|
| `model/QuaternionTest.kt` | 11 tests: slerp, identity, FaceParams lerp, confidence levels | Pass |
| `translation/AslGrammarRulesTest.kt` | 15 tests: articles, copula, WH-questions, negation, time, contractions, directional verbs | Pass |
| `translation/PatternHashTableTest.kt` | 10 tests: exact match, slot extraction, case sensitivity | Pass |
| `stt/VadProcessorTest.kt` | 6 tests: silence, speech detection, reset | Pass |

**Total: 42 tests, all passing.**

### Tools — `tools/`

| File | Purpose |
|------|---------|
| `generate_avatar_glb.py` | Generates procedural 48-joint humanoid GLB |

---

## Key Decisions Made

| Decision | Rationale |
|----------|-----------|
| Telegram overlay, not standalone app | Telegram handles calls, contacts, presence — don't rebuild |
| Bot relay (Path B) | Path A dead — Android blocks voice call audio capture at OS level |
| Vosk STT (on-device, free) | No API key required. MiniLM upgrade optional for tier 2 accuracy |
| Kotlin native Android | Best GPU control for avatar rendering. Not React Native/Flutter |
| OpenGL ES 2.0 | Widest device support. 3D for audio calls, 2D sprites for video calls |
| ASL grammar in V1 | 3-tier: pattern hash → vector similarity → rule-based grammar transform |
| No account | Device-local preferences only. Relay URL entered in settings |
| Apache 2.0 license | Patent protection for ML models and processing pipeline |
| F-Droid / sideload, not Play Store | Potential Telegram ToS friction with audio capture |

---

## What's NOT Built

| Item | Why |
|------|-----|
| Tier 3 (T5-small model) | Insufficient English↔ASL parallel training data |
| iOS | V2 roadmap |
| Hebrew Sign Language | V2, after English/ASL validated |
| WhatsApp support | WhatsApp API doesn't allow bot call joining |
| Sign recognition (camera → voice) | V2, hard ML problem |
| Custom avatar appearance | Need artist-made model first |
| Push notifications for incoming calls | Relay server would need to detect calls |
| End-to-end encryption | Audio passes through relay server |

---

## How to Build

```bash
# Android
export ANDROID_HOME=/path/to/android-sdk
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk

# Tests
./gradlew testDebugUnitTest

# Dictionary rebuild
python3 -c "
from dictionary.build.common_signs import get_all_common_sign_entries
from dictionary.build.common_signs_extended import get_all_extended_entries
from dictionary.build.builder import build_dictionary
signs = list(get_all_common_sign_entries().values()) + list(get_all_extended_entries().values())
build_dictionary(signs)
"
python3 dictionary/build/convert_for_app.py dictionary/output/dictionary.json app/src/main/assets/dictionary/signs.json

# Relay server
cd relay
pip install -r requirements.txt
export TELEGRAM_PHONE="+1234567890"
export TELEGRAM_APP_ID="12345"
export TELEGRAM_APP_HASH="abcdef"
uvicorn main:app --host 0.0.0.0 --port 8080
```

---

## File Counts

| Category | Count |
|----------|-------|
| Kotlin source files | 25 |
| Kotlin test files | 4 (42 tests) |
| Python source files | ~40 |
| GLSL shaders | 2 |
| JSON data files | 4 |
| GLB model | 1 |
| Total project files | ~100 (excluding build artifacts) |
| APK size (debug) | 108MB |
| Sign dictionary | 115 signs |
| Translation patterns | 224 |
| Vector embeddings | 378 |
