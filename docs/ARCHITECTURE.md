# SignBridge — Architecture

## Overview

SignBridge is an Android overlay app. It sits on top of Telegram, captures call audio via a relay bot, translates speech to ASL gloss, and renders a 3D avatar signing the result in real time.

```
┌─────────────────────────────────────────────────────────────┐
│                        Android Phone                         │
│                                                             │
│  ┌────────────┐    ┌──────────────────────────────────────┐ │
│  │  Telegram  │    │         SignBridge App               │ │
│  │   (call)   │    │                                      │ │
│  └────────────┘    │  ┌──────────┐   ┌─────────────────┐ │ │
│        │           │  │ Silero   │   │  ASL Translation │ │ │
│        │           │  │   VAD    │   │     Engine       │ │ │
│        ▼           │  └────┬─────┘   │  ┌────────────┐  │ │ │
│  ┌─────────────┐   │       │         │  │ PatternHash│  │ │ │
│  │ Relay Server│──▶│  ┌────▼─────┐   │  │ VectorSim  │  │ │ │
│  │ (pytgcalls) │   │  │  Vosk    │──▶│  │ GrammarRule│  │ │ │
│  └─────────────┘   │  │  STT     │   │  └─────┬──────┘  │ │ │
│    WebSocket        │  └──────────┘   └────────┼────────┘ │ │
│    raw PCM          │                          │           │ │
│                    │  ┌────────────────────────▼─────────┐ │ │
│                    │  │      Sign Dictionary (115 signs)  │ │ │
│                    │  └────────────────────────┬─────────┘ │ │
│                    │                           │            │ │
│                    │  ┌────────────────────────▼─────────┐ │ │
│                    │  │   Avatar Renderer (OpenGL ES)     │ │ │
│                    │  │   ┌─────────────┐ ┌───────────┐  │ │ │
│                    │  │   │ 3D / LBS    │ │ 2D Sprite │  │ │ │
│                    │  │   │ audio calls │ │ video mode│  │ │ │
│                    │  │   └─────────────┘ └───────────┘  │ │ │
│                    │  └──────────────────────────────────┘ │ │
│                    │                                        │ │
│                    │  Floating overlay (SYSTEM_ALERT_WINDOW)│ │
│                    └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Why a Relay Bot?

Android's `AudioPlaybackCapture` API **cannot capture voice call audio**. This is an OS-level restriction confirmed from AOSP source code:

- Only `USAGE_MEDIA`, `USAGE_GAME`, `USAGE_UNKNOWN` are capturable
- `USAGE_VOICE_COMMUNICATION` is hardcoded excluded
- Telegram uses `USAGE_VOICE_COMMUNICATION` for all calls
- No app-level workaround exists

The relay bot (pytgcalls) joins the call via MTProto, captures audio server-side, and streams raw PCM over WebSocket to the app.

---

## Components

### Android App (`app/`)

| Package | Responsibility |
|---------|---------------|
| `audio/` | `RelayClient` — WebSocket client, receives PCM from relay server |
| `stt/` | `VadProcessor` (energy-based VAD) + `VoskSttEngine` (on-device STT) + `SttPipeline` orchestrator |
| `translation/` | 3-tier ASL engine: `PatternHashTable` → `VectorSimilarityIndex` → `AslGrammarRules` |
| `renderer/` | `AvatarRenderer` (OpenGL ES + GLTF/LBS), `SpriteAvatarRenderer` (2D Canvas), `GltfLoader`, `ShaderProgram` |
| `overlay/` | `OverlayService` — foreground service that draws on top of all apps |
| `model/` | Shared types: `Quaternion` (slerp), `FaceParams` (lerp), `SignEntry`, `SignSequence`, `PipelineStatus` |
| `ui/` | `MainActivity`, `SetupActivity`, `DemoActivity` |
| `settings/` | `SettingsActivity` |
| `util/` | `Preferences` — all local settings, no server |

### Relay Server (`relay/`)

FastAPI + pytgcalls. Joins Telegram voice/group calls as a user account, streams raw 16kHz mono PCM to Android over WebSocket.

```
POST /session/start  {"chat_id": 123}  → {"session_id": "abc", "audio_url": "ws://..."}
POST /session/end    {"session_id": "abc"}
GET  /audio/{id}     WebSocket — binary PCM frames
GET  /health
```

Requires: Telegram `api_id`, `api_hash`, phone number (from my.telegram.org/apps).

### ASL Translation Engine (`agent4/`)

Three-tier cascade:

| Tier | Method | Speed | Coverage |
|------|--------|-------|----------|
| 1 | Pattern hash with `{SLOT}` templates | < 1ms | ~50% of conversational sentences |
| 2 | MiniLM-L6-v2 sentence embeddings + cosine similarity | ~5ms | +30% via semantic matching |
| 3 | Grammar rules (topic-comment, WH-end, negation-after-verb) | < 1ms | 100% fallback |

### Sign Dictionary (`dictionary/`)

MediaPipe extraction pipeline: video → hand landmarks → keyframe selection → IK solve → quaternion bone rotations → `signs.json`.

Current: 115 signs (79 content + 26 A-Z + 10 0-9).
Format: per-bone quaternion keyframes at 30fps, continuous face expression parameters.

---

## Data Flow

```
Relay PCM frames (16kHz mono)
  → VadProcessor (detects utterance boundaries)
  → VoskSttEngine (on-device ASL → English text + confidence)
  → AslTranslationEngine (English → ASL gloss tokens)
  → SignDictionary.lookupGloss() (gloss → keyframe sequences + fingerspelling)
  → AvatarRenderer.playSignSequence() (animate bones via quaternion slerp)
  → GLSurfaceView overlay (renders on top of Telegram)
  + subtitle bar always showing recognized English text
  + confidence indicator (green/yellow/red glow)
```

---

## Rendering

### Audio Call Mode (3D)
- OpenGL ES 2.0, `GLSurfaceView`
- GLTF 2.0 / GLB model with 48 named joints
- **Linear Blend Skinning (LBS)**: 4 joint influences per vertex, 48 bone matrices as uniforms
- Vertex shader: `avatar_vert.glsl` — LBS transform
- Fragment shader: `avatar_frag.glsl` — Lambertian diffuse + fresnel confidence glow
- Keyframe animation: quaternion slerp between frames
- Transition paths: custom keyframe sequences for sign-to-sign movement

### Video Call Mode (2D)
- Android `Canvas` + `SurfaceView`
- Simplified avatar (circle head, rectangle torso, line-segment arms)
- Bone quaternions projected to 2D screen positions
- Lower GPU load — avoids contention with Telegram's video decode

---

## Sign Format

```json
{
  "hello": {
    "sign_id": "hello",
    "gloss": "HELLO",
    "duration_ms": 400,
    "category": "greeting",
    "frames": [
      {
        "time_ms": 0,
        "bones": {
          "right_wrist": { "rotation": [0.0, 0.0, 0.0, 1.0] },
          "right_index_mcp": { "rotation": [0.1, 0.0, 0.0, 0.995] }
        },
        "face": {
          "eyebrow_raise": 0.7,
          "mouth_open": 0.2,
          "head_tilt": 0.0,
          "eye_gaze_x": 0.0,
          "cheek_puff": 0.0
        }
      }
    ]
  }
}
```

Joint set: 21 per hand × 2 = 42 hand bones + 6 body + spine + head = 50 total.
Face: 5 continuous parameters (0.0–1.0).

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Telegram overlay, not standalone | Telegram provides calls, contacts, presence for free |
| Bot relay (not AudioPlaybackCapture) | OS-level restriction on voice call audio capture |
| Vosk (on-device STT) | Free, no API key, works offline |
| MiniLM for tier 2 | 384-dim sentence embeddings, 86MB ONNX, fast on CPU |
| Kotlin native (not React Native/Flutter) | Full GPU control for skinned mesh rendering |
| OpenGL ES 2.0 | Max device compatibility (API 29+) |
| Quaternion keyframes | Drives GLTF rig directly, smooth slerp interpolation |
| Apache 2.0 license | Patent protection for ML pipeline |
| F-Droid / sideload | Telegram ToS risk with audio capture |

---

## Minimum Requirements

- Android 10 (API 29) — required for AudioPlaybackCapture API (even though Path A is dead, keeps the API surface clean)
- Snapdragon 600 series or equivalent — 30fps target
- ~200MB storage after first launch (Vosk model + MiniLM)
- Internet for relay WebSocket connection during calls

---

## Adding a Real Avatar

The current `avatar.glb` is a procedural placeholder (17KB, 187 vertices). To replace:

1. Model a friendly cartoon humanoid in Blender (upper body only)
2. Rig with bones named exactly as in `tools/generate_avatar_glb.py` (48 joints)
3. Include: `POSITION`, `NORMAL`, `JOINTS_0`, `WEIGHTS_0` vertex attributes
4. Export as GLB, place at `app/src/main/assets/models/avatar.glb`
5. Renderer loads it automatically — no code changes needed
