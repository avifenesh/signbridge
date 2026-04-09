# SignBridge — Product Specification V1

## Vision

An open source Android app that gives deaf people real-time ASL signing
during any Telegram voice or video call. The hearing person speaks normally.
The deaf person sees a cartoon avatar signing everything said, rendered as
a floating overlay on top of Telegram — with recognized English text always
visible as subtitles for cross-referencing.

Free for everyone. No server dependency. Works out of the box with zero setup cost.

**Minimum Android version: API 29 (Android 10).** Required for AudioPlaybackCapture.

---

## How It Works

```
1. Deaf person starts or receives a Telegram call — normal Telegram call
2. Deaf person activates SignBridge overlay
3. SignBridge bot joins the call (visible as participant), captures audio
4. Audio streamed to phone over WebSocket
5. Silero VAD detects speech boundaries on-device
6. Audio → Vosk STT (on-device, streaming) → English text
7. English → ASL translation (3-tier: pattern hash → vector similarity → grammar rules)
8. ASL sign sequence → avatar keyframe animation
9. Avatar renders as floating overlay on top of Telegram
10. Recognized English text always shown as subtitle under avatar
```

Everything runs on the phone except audio capture. STT, translation, and rendering
are all on-device. No API key required for default experience (Vosk STT is free/local).

### Audio Capture — Path B (Bot Relay) — PRIMARY

**VALIDATED: AudioPlaybackCapture (Path A) CANNOT capture Telegram call audio.**

Research confirmed from AOSP source code:
- Android only allows AudioPlaybackCapture of `USAGE_MEDIA`, `USAGE_GAME`, `USAGE_UNKNOWN`
- `USAGE_VOICE_COMMUNICATION` is hardcoded excluded at the OS audio policy level
- Telegram uses `USAGE_VOICE_COMMUNICATION` for all 1:1 and group calls
- No app-level workaround exists — the restriction is in the OS kernel

**Path B (bot relay) is the only viable architecture:**
- Telegram bot joins the call via pytgcalls, captures audio server-side
- Streams raw PCM audio to the phone over WebSocket
- Phone does all processing (STT, translation, rendering)
- Requires a minimal relay server (~$1/month to self-host)
- **The hearing person WILL see the bot as a call participant.** The deaf user
  is clearly informed of this during setup.

Path A code remains in the codebase for potential future use with other apps
or if Android relaxes the restriction.

---

## Open Source Model

- Fully open source — Apache 2.0 license
- Free for everyone
- No SignBridge account, no subscription
- Default STT: Vosk (on-device, free, no API key needed)
- Vosk English model (~50MB) downloaded on first launch (not bundled in APK)
- Optional upgrade: user can plug in a cloud STT key (Groq, Deepgram, Google) for higher accuracy
- No data collection, no analytics, no telemetry
- Distribution: F-Droid + GitHub releases (not Google Play — potential ToS conflicts with Telegram audio capture)
- Sideloading instructions in README

---

## Users

| User | What they do | What they need |
|------|-------------|----------------|
| Deaf user | Makes/receives Telegram calls | Installs SignBridge — that's it |
| Hearing user | Talks normally on Telegram | Nothing. They don't know SignBridge exists. |

---

## What Telegram Gives Us (Free)

- Call infrastructure (audio + video)
- Contact list and identity
- Presence / availability
- Push notifications
- Incoming/outgoing calls in both directions
- Cross-platform (hearing person can be on any device)

## What We Build

- Android overlay app with avatar renderer
- On-device audio capture (Path A) or thin bot relay (Path B)
- On-device STT (Vosk default, optional cloud upgrade)
- On-device VAD (Silero)
- ASL translation engine (3-tier)
- ASL sign dictionary
- Fingerspelling system

---

## Telegram ToS Risk

Both paths potentially interact with Telegram in ways their ToS may not explicitly allow:
- Path A: captures audio output from Telegram via Android system API
- Path B: uses unofficial tgcalls library to join calls programmatically

Mitigations:
- Distribute via F-Droid and GitHub, not Google Play
- Provide sideloading instructions
- If project gains traction, pursue accessibility partnership with Telegram directly
- This is an accessibility tool for deaf users — strong public interest argument

---

## Call Modes

### Audio Call (Telegram voice call)
- Overlay: full screen avatar on top of Telegram's call screen
- Deaf person sees avatar signing everything the hearing person says
- English subtitle text always visible under avatar

### Video Call (Telegram video call)
- Overlay: avatar in bottom-right corner on top of Telegram's video
- Tap avatar → expands to full screen
- Tap again → returns to corner
- **Video call mode uses 2D sprite animation** (not full 3D) to reduce GPU
  contention with Telegram's video decode. Audio call mode uses full 3D.
- English subtitle text visible near avatar

Camera toggling handled by Telegram — both sides can toggle freely.

---

## Deaf Person Response Modes

| Mode | How | Built by |
|------|-----|----------|
| **Speak** | Talk into mic normally via Telegram | Telegram |
| **Type** | Telegram chat alongside the call | Telegram |
| **Quick phrases** | Tap buttons on overlay → sent as Telegram chat messages | SignBridge |

Quick phrases are the only response mode we build. Speak and type are handled by Telegram.
Quick phrases are customizable by the user.

**Honest limitation:** Quick phrases are sent as Telegram text messages. During a voice call,
the hearing person may not be looking at their screen and won't hear an audio cue.
Quick phrases are an asynchronous response channel, not real-time. They speed up typing,
but if the deaf person can speak at all, speaking is always the faster path.

TTS injection into Telegram's call audio is not possible on stock Android without root.

---

## Avatar + Subtitles

### Style
- Friendly cartoon humanoid
- Upper body: head, neck, shoulders, arms, hands
- Hands slightly larger than realistic for readability
- Facial expressions (eyebrows, mouth) — carry grammatical meaning in ASL

### Subtitle Bar
- Recognized English text always displayed as a subtitle below the avatar
- Allows deaf user to cross-reference: see what was said AND how it was signed
- Helps catch STT errors that would otherwise produce wrong signs silently
- Font size configurable in settings

### Confidence Indicator
- Avatar border/glow shifts color based on pipeline confidence:
  - Green: high confidence (STT + translation both confident)
  - Yellow: medium (one stage uncertain)
  - Red: low confidence → auto-fallback to captions-only mode
- Gives the deaf user a signal to trust, question, or ask for a repeat

### Rendering — Audio Call Mode
- Android overlay using `SYSTEM_ALERT_WINDOW` permission
- OpenGL ES via SurfaceView
- GLTF rigged 3D model driven by bone rotations (quaternions)
- Keyframe animation at 30fps
- Smooth interpolation between signs (slerp on quaternions)
- Sign transitions: dictionary includes optional transition data per sign pair

### Rendering — Video Call Mode
- 2D pre-rendered sprite animation (lighter GPU load)
- Same sign content, different rendering method
- Allows Telegram video decode + avatar to coexist on mid-range hardware

---

## ASL Translation Engine — 3 Tiers

The pipeline does NOT do word-for-word English substitution. ASL has its own grammar.

Full sentence is captured, then translated to ASL gloss before signing:

```
English sentence (from STT)
        ↓
Tier 1: Pattern hash — template match → ASL gloss (instant)
        ↓ miss
Tier 2: Vector similarity — closest known pattern → adapted ASL gloss (fast)
        ↓ low confidence
Tier 3: Small fine-tuned model — generate ASL gloss (slower, handles anything)
        ↓
ASL gloss → sign sequence lookup → avatar animation
```

### Tier 1 — Pattern Hash Table (Detail)

NOT exact string matching. Uses **template patterns** with slots:

```
Pattern: "I gave {PERSON} the {OBJECT}"
ASL template: {OBJECT} I GIVE-{PERSON}

Pattern: "What is your {NOUN}?"
ASL template: YOUR {NOUN} WHAT

Pattern: "I don't {VERB}"
ASL template: {VERB} I NOT
```

- Patterns extracted from common English sentence structures
- Slots filled with the actual words from the input
- Hand-curated: a few thousand templates covers a large percentage of conversational English
- Lookup: normalize input → match against pattern index → fill ASL template
- Hit rate: estimated 30-50% of conversational sentences match a pattern

### Tier 2 — Vector Similarity (Detail)

When no pattern matches exactly:

- **Embedding model:** MiniLM-L6 (22MB, ONNX) — encodes English sentences into 384-dim vectors
- **Index:** FAISS flat index of all known English patterns + their ASL glosses
- **Lookup:** embed input sentence → find top-3 nearest patterns → select best match
- **Adaptation:** if the matched pattern has slots, extract corresponding words from
  the input sentence and fill them into the ASL template. If no slots, use the matched
  ASL gloss directly.
- **Confidence threshold:** cosine similarity > 0.75 → use match. Below 0.75 → fall to tier 3.
- **Index size:** ~5MB for 10K pattern vectors (384 dims × 4 bytes × 10K = ~15MB raw,
  compressed with product quantization to ~5MB)

### Tier 3 — Small Fine-Tuned Model (Detail)

- Base: T5-small (60M params) or ByT5-small, fine-tuned on English → ASL gloss
- Target ONNX export size: < 20MB (quantized INT8)
- Target inference: < 200ms on Snapdragon 600 via NNAPI
- Ships as "experimental" in V1 if training data is insufficient
- Tiers 1+2 carry the primary load; tier 3 is a progressive enhancement

### Examples
| English | Tier | ASL Gloss |
|---------|------|-----------|
| "I gave you the book" | 1 (pattern: "I gave {P} the {O}") | BOOK I GIVE-YOU |
| "What is your name?" | 1 (pattern: "What is your {N}?") | YOUR NAME WHAT |
| "The weather looks nice today" | 2 (similar to "The weather is nice") | TODAY WEATHER NICE |
| "I can't believe she said that" | 3 (model generates) | SHE SAY THAT BELIEVE I CAN'T |

### Training Data
- Scraped from legally available sources only — each individually verified before use
- English ↔ ASL parallel corpora from educational resources, university publications
- Known datasets to evaluate: ASLG-PC12, NCSLGR, Gallaudet resources
- **Each source must be individually verified for licensing before inclusion**
- Realistic expectation: a few thousand parallel sentences available
- If data is insufficient for tier 3, ship V1 with tiers 1+2 only

### STT Error Handling
- STT errors are a normal condition, not an edge case — design for them
- Vosk will produce errors especially with accented speech, background noise, domain vocabulary
- Mitigations:
  1. English subtitle always visible — deaf user can read the text and spot errors
  2. Confidence indicator on avatar — signals when pipeline is uncertain
  3. Low STT confidence → captions-only mode (don't sign garbage)
  4. Tier 2 vector similarity is naturally error-tolerant: "I gave you the brook"
     still matches close to "I gave you the book" in embedding space

---

## Fingerspelling

Words not in the sign dictionary are fingerspelled — letter by letter using
the ASL manual alphabet. This covers:
- Names
- Technical terms
- Addresses
- Numbers (ASL number signs 0-9)

**No word is ever skipped.** If it's not in the dictionary, it's fingerspelled.

26 hand shapes (A-Z) + 10 number signs (0-9) = 36 static poses.

---

## Real-Time Pipeline

### Path A (fully on-device)
```
Hearing person speaks (Telegram call)
        ↓
Android AudioPlaybackCapture captures audio
        ↓
Silero VAD (on-device) detects speech / silence boundaries
        ↓
On silence: utterance chunk → Vosk STT (on-device, streaming)
  (Optional: user upgrades to cloud STT — Groq/Deepgram/Google — for accuracy)
        ↓
English sentence detected
        ↓
ASL Translation Engine (3-tier) → ASL gloss
        ↓
ASL gloss → sign lookup → keyframe sequence (quaternion-based)
Unknown words → fingerspelling
        ↓
IK solver converts any position-based data to bone rotations
        ↓
Avatar renders signs as floating overlay + subtitle text
```

### Path B (bot relay fallback)
```
Hearing person speaks (Telegram call)
        ↓
SignBridge bot (server) captures audio via tgcalls
        ↓
Audio streamed to phone
        ↓
(same pipeline as Path A from here)
```

### Latency Targets
| Stage | Target |
|-------|--------|
| VAD silence detection | ~100ms after speech ends |
| Vosk STT (on-device streaming) | ~200ms |
| Cloud STT — Groq (if upgraded) | ~500-800ms (batch, includes network) |
| ASL translation (tier 1 pattern) | < 20ms |
| ASL translation (tier 2 vector) | < 100ms |
| ASL translation (tier 3 model) | < 200ms |
| Sign lookup + IK + keyframe prep | < 50ms |
| **Total with Vosk: sentence end → avatar starts** | **~400-500ms** |
| **Total with Groq: sentence end → avatar starts** | **~800ms-1.2s** |

Note: TV sign language interpreters have ~1-2s delay. Both targets are acceptable.

---

## MediaProjection UX — "Always Ready" Mode

AudioPlaybackCapture requires MediaProjection permission, which shows a system dialog
every time. This cannot be permanently granted. To avoid the deaf user fumbling with
dialogs when a call comes in:

**"Always Ready" mode:**
- User activates SignBridge once when they start their day
- MediaProjection stays active in the background (persistent notification required)
- When a Telegram call comes in, the overlay activates instantly — no dialog
- User deactivates at end of day or when not expecting calls

This trades a persistent notification for instant call readiness.
Battery impact of idle MediaProjection to be validated during Phase 1 — estimate ~2-3%/hour
but may be higher.

---

## Fallback Behavior

| Condition | Behavior |
|-----------|----------|
| STT lag | Avatar freezes at last pose, subtitle shows "..." |
| Low STT confidence | Confidence indicator turns yellow/red, subtitle shows text |
| Pipeline failure > 2s | "Reconnecting..." indicator on overlay |
| Full pipeline failure > 5s | Captions mode — text overlay instead of avatar |
| STT confidence below 0.3 | Auto-switch to captions for that sentence (don't sign garbage) |
| Audio capture fails | Prompt user to check permissions or switch to Path B |
| OS kills overlay (resource pressure) | Notification: "SignBridge paused — tap to restart" |

---

## Privacy & Security

### Path A (fully on-device — default)
- Audio never leaves the phone (Vosk runs locally)
- If user opts into cloud STT: audio sent to their chosen provider with their own API key
- No SignBridge server involved
- No data stored anywhere
- Hearing person has zero indication SignBridge is running

### Path B (bot relay)
- Audio passes through a relay bot server
- Audio is NOT stored — streamed in real-time and discarded
- **Bot is a visible participant in the Telegram call**
- **Hearing person WILL see the bot join** — this is communicated clearly to the deaf user during setup

---

## Technical Architecture

### Path A
```
[Telegram App]
      │
  Audio output
      ↓
[Android AudioPlaybackCapture]
      │
      ↓
[Silero VAD] ──→ speech boundary detection
      │
      ↓
[Vosk STT] (on-device, streaming)        ── OR ──  [Cloud STT] (Groq/Deepgram, optional)
      │                                                   │
      ↓                                                   ↓
          English sentence + confidence
                     ↓
          [ASL Translation Engine]
           Pattern Hash → Vector (MiniLM) → Model (T5-small)
                     │
                ASL gloss + confidence
                     ↓
          [Sign Dictionary Lookup]
                     │
              Bone rotations (quaternions)
                     ↓
              [IK Solver] (if needed for position→rotation conversion)
                     ↓
[SignBridge Overlay] ←─────── [Avatar Renderer]
  (on top of Telegram)         (OpenGL ES / 2D sprites)
  + subtitle bar                + confidence indicator
```

### Path B
```
[Telegram App]                    [SignBridge Android App]
      │                                    │
  Normal call                        Floating overlay
      │                              (avatar renderer)
      ↓                                    ↑
[Telegram Servers]                 [same pipeline as A]
      │                                    ↑
      ↓                              audio stream
[Bot Relay Server] ─────────────────→ [Phone]
  (tgcalls, audio only)
```

### Components

| Component | Tech | Runs on | Size |
|-----------|------|---------|------|
| Audio capture | AudioPlaybackCapture API (Path A) | Phone | — |
| VAD | Silero VAD | Phone | ~2MB |
| STT (default) | Vosk (English model, downloaded on first launch) | Phone | ~50MB (model) |
| STT (optional) | Groq / Deepgram / Google Cloud | Cloud (user's key) | — |
| Sentence embedding | MiniLM-L6 (ONNX) | Phone | ~22MB |
| ASL translation tier 1 | Pattern hash table (JSON) | Phone | ~2MB |
| ASL translation tier 2 | FAISS product-quantized index | Phone | ~5MB |
| ASL translation tier 3 | T5-small (ONNX, INT8 quantized) | Phone | ~20MB |
| IK solver | Lightweight analytical IK | Phone | — |
| Sign lookup | In-memory dictionary | Phone | — |
| Avatar renderer (audio) | Kotlin + OpenGL ES | Phone | — |
| Avatar renderer (video) | Kotlin + 2D sprites | Phone | — |
| Avatar model | GLTF rigged model | Phone | ~5MB |
| Sign dictionary | Quaternion keyframes (binary) | Bundled in app | ~10MB |
| Fingerspelling | 36 static poses | Bundled in app | < 1MB |
| Bot relay (Path B only) | Python + tgcalls | Minimal server | — |

**Estimated APK size: ~40MB** (Vosk model + MiniLM downloaded on first launch: +72MB)
**Total on-device after setup: ~112MB**

---

## API Contracts

### Internal — STT Output

```json
{
  "sentence": "I gave you the book",
  "confidence": 0.94,
  "source": "vosk"
}
```

### Internal — ASL Translation Engine Output

```json
{
  "asl_gloss": ["BOOK", "I", "GIVE-YOU"],
  "method": "pattern_hash",
  "pattern": "I gave {PERSON} the {OBJECT}",
  "confidence": 1.0
}
```

### Internal — Sign Sequence Format

```json
{
  "type": "sign_sequence",
  "english": "I gave you the book",
  "pipeline_confidence": 0.91,
  "gloss": ["BOOK", "I", "GIVE-YOU"],
  "signs": [
    {
      "gloss": "BOOK",
      "type": "sign",
      "sign_id": "book",
      "duration_ms": 600
    },
    {
      "gloss": "I",
      "type": "sign",
      "sign_id": "i_me",
      "duration_ms": 300
    },
    {
      "gloss": "GIVE-YOU",
      "type": "sign",
      "sign_id": "give_directional_you",
      "duration_ms": 700
    }
  ]
}
```

Fingerspelled word:
```json
{
  "gloss": "SARAH",
  "type": "fingerspell",
  "letters": ["S", "A", "R", "A", "H"],
  "duration_ms": 1500
}
```

Status events (internal):
```json
{ "type": "status", "state": "listening" }
{ "type": "status", "state": "processing" }
{ "type": "status", "state": "signing", "pipeline_confidence": 0.91 }
{ "type": "status", "state": "error", "fallback": "caption", "text": "I gave you the book" }
```

### Path B Only — Bot Relay API

| Endpoint | Purpose |
|----------|---------|
| WebSocket | Bot streams raw audio to phone |
| `POST /session/start` | App tells bot: join this call |
| `POST /session/end` | App tells bot: leave call |

---

## Sign Dictionary

### Format

Keyframes store **bone rotations (quaternions)**, not world-space positions.
This drives the GLTF rig directly without an IK step for pre-captured signs.
IK solver is only needed if converting from MediaPipe position data at extraction time.

```json
{
  "book": {
    "sign_id": "book",
    "gloss": "BOOK",
    "duration_ms": 600,
    "category": "object",
    "frames": [
      {
        "time_ms": 0,
        "bones": {
          "right_wrist": { "rotation": [0.0, 0.0, 0.0, 1.0] },
          "right_index_proximal": { "rotation": [0.1, 0.0, 0.0, 0.995] },
          "right_index_intermediate": { "rotation": [0.2, 0.0, 0.0, 0.98] },
          "right_thumb_proximal": { "rotation": [0.0, 0.1, 0.0, 0.995] }
        },
        "face": {
          "eyebrow_raise": 0.0,
          "mouth_open": 0.1,
          "head_tilt": 0.0,
          "eye_gaze_x": 0.0,
          "cheek_puff": 0.0
        }
      },
      {
        "time_ms": 300,
        "bones": { "...": "..." },
        "face": { "...": "..." }
      }
    ]
  }
}
```

### Bone Set
- 21 bones per hand (matching MediaPipe hand model) × 2 hands = 42 hand bones
- Each bone stores a rotation quaternion [x, y, z, w] — captures curl, spread, and pronation
- 6 upper body bones (shoulders, elbows, wrists) — also quaternion rotations
- Total: 48 bone rotations per frame (4 floats each = 192 floats per frame)

### Facial Parameters (Continuous Values 0.0–1.0)
- `eyebrow_raise` — 0.0 neutral, 1.0 fully raised
- `mouth_open` — 0.0 closed, 1.0 fully open (with shape variants: smile, frown, etc.)
- `head_tilt` — -1.0 left, 0.0 center, 1.0 right
- `eye_gaze_x` — -1.0 left, 0.0 center, 1.0 right
- `cheek_puff` — 0.0 neutral, 1.0 fully puffed

Continuous values enable smooth blending between facial expressions during transitions.

### Sign Transitions
- Default: slerp interpolation on quaternions between end pose of sign A and start pose of sign B
- Some sign pairs require specific movement paths (e.g., contact signs, directional verbs)
- Dictionary includes optional `transitions` entries:

```json
{
  "transition_id": "book_to_i_me",
  "from_sign": "book",
  "to_sign": "i_me",
  "duration_ms": 200,
  "frames": [
    {
      "time_ms": 0,
      "bones": { "...": "..." },
      "face": { "...": "..." }
    },
    {
      "time_ms": 200,
      "bones": { "...": "..." },
      "face": { "...": "..." }
    }
  ]
}
```

- If a transition entry exists for a sign pair, play it between the two signs
- If no transition entry, use default slerp interpolation (200ms)
- Transition quality is critical for readability — robotic transitions make ASL hard to understand
- Movement dynamics (speed, acceleration) distinguish some signs (e.g., CHAIR vs SIT) — keyframe
  timing within the sign handles this

### Quality Metric
- Each sign must be validated for readability by an ASL-fluent person
- Quality score: 1-5 scale (1 = unreadable, 5 = native-quality)
- V1 minimum: score 3+ for all included signs
- 50 clean, validated signs > 500 noisy ones

### V1 Dictionary Scope
- Target: 500 most common ASL signs (sourced from ASL-LEX frequency data)
- 26 fingerspelling hand shapes (A-Z)
- 10 number signs (0-9)
- Source: MediaPipe pose extraction from open ASL video datasets → IK solve → quaternion keyframes
- **All sources individually verified for licensing before inclusion**
- Expansion timeline: Phase 3 delivers 50 seed signs. Phase 3→6 expands to 500 progressively.
  Dictionary pipeline (Agent 3) continues producing signs throughout development.

### Estimated Dictionary Size
- 192 floats/frame × 4 bytes × ~10 frames/sign × 536 signs = ~41MB raw
- Binary format (not JSON) for production: ~10MB with compression
- Plus transitions, metadata: ~12MB total
- Within budget

---

## Screens — Android App

### 1. Setup (one time)
- Grant overlay permission (SYSTEM_ALERT_WINDOW)
- Grant audio capture permission (MediaProjection for Path A)
- Grant notification permission (Android 13+)
- Download Vosk English model (~50MB, one-time)
- Download MiniLM embedding model (~22MB, one-time)
- Optional: enter cloud STT API key for higher accuracy
- Choose default response mode

### 2. Home
- Status: ready / always-ready active / overlay active
- "Always Ready" toggle (pre-activates MediaProjection)
- Start overlay button
- Quick phrases customization
- Settings

### 3. Overlay — Audio Call Mode
- Full screen semi-transparent overlay on top of Telegram
- Avatar centered, 3D OpenGL ES rendering
- Subtitle bar below avatar (always visible, shows recognized English text)
- Confidence indicator (avatar border glow: green/yellow/red)
- Bottom bar: quick phrase buttons (customizable)
- Minimize button → shrinks to floating bubble
- Caption text area (enlarged, shown when confidence fallback active)

### 4. Overlay — Video Call Mode
- Small avatar in bottom-right corner, 2D sprite rendering
- Subtitle text near avatar
- Confidence indicator
- Tap → expand to full screen
- Tap again → return to corner
- Quick phrase buttons
- Caption text area (enlarged when fallback active)

### 5. Settings
- STT: on-device (default) or cloud (enter API key + select provider)
- Quick phrase editor (add/remove/reorder)
- Avatar size preference
- Subtitle font size
- Confidence indicator: on/off
- Fallback mode: auto / always captions / always avatar
- Path A/B toggle (if both available)
- Battery saver mode (reduce avatar framerate to 15fps)

---

## Performance Budget

### Audio Call Mode (3D avatar)
- OpenGL ES rendering: ~30% GPU
- Vosk STT: ~15% CPU
- MiniLM embedding (burst): ~5% CPU
- ASL translation: < 5% CPU (burst)
- Total additional RAM: ~100MB
- Target: 30fps avatar on Snapdragon 600

### Video Call Mode (2D sprites)
- Telegram video decode: ~20-30% GPU
- 2D sprite overlay: ~5% GPU
- Vosk STT: ~15% CPU
- MiniLM embedding (burst): ~5% CPU
- ASL translation: < 5% CPU (burst)
- Total additional RAM: ~80MB
- Target: 30fps sprites, no jank on video

### Battery
- Expect ~20-30% additional battery drain during active calls compared to Telegram alone
- Battery saver mode available: 15fps, reduced sprite quality
- "Always Ready" mode (MediaProjection idle): to be validated in Phase 1

---

## Testing Strategy

### Unit Tests
- ASL translation engine: given English input X, expect ASL gloss Y
- Pattern hash: verify template matching and slot filling
- Vector similarity: verify nearest-neighbor retrieval and adaptation
- Sign lookup: verify gloss → keyframe sequence mapping
- Fingerspelling: verify word → letter sequence

### Integration Tests
- Audio file → full pipeline → expected sign sequence (recorded test cases)
- STT error injection: feed known-bad audio → verify graceful degradation
- Confidence thresholds: verify fallback triggers at correct levels

### Contract Tests (Between Agents)
- Agent 4 output (ASL gloss) consumed correctly by Agent 1a (renderer)
- Agent 3 output (dictionary) loaded correctly by Agent 1a (renderer)
- Agent 1b (app shell) integrates correctly with Agent 1a (renderer)
- Define test fixtures that all agents validate against

### Dictionary Regression
- Each sign has a test case: sign_id → renders without error → visual output validated
- Automated: no render crashes, correct bone count, animation duration matches spec
- Manual: readability validation by ASL-fluent person (quality score 3+)

### Performance Benchmarks
- Measure actual fps on Snapdragon 600 reference device
- Measure pipeline latency end-to-end with test audio
- Measure memory footprint during active call
- Run in CI on every merge (Android emulator for functional, device farm for perf)

---

## Abuse Protection

- No server = no abuse vector for Path A
- Path B: bot only joins calls when the deaf user explicitly activates
- Rate limiting on bot relay (Path B): max sessions per user per hour
- DND mode in overlay settings

---

## Out of Scope — V1

- iOS
- Sign recognition (camera reads deaf person's signs → voice)
- Languages other than English / ASL
- WhatsApp / regular phone call support
- Standalone call infrastructure (WebRTC, PSTN)
- Call recording
- Group calls
- Custom avatar appearance (skin, clothing)
- Analytics / telemetry (intentionally omitted — open source ethos)
- Google Play distribution

---

## V2 Roadmap (Not Built Now)

- WhatsApp integration (if API allows)
- iOS app
- Hebrew Sign Language (ISL)
- Custom avatar appearance
- Standalone calls (no Telegram dependency)
- Group call support
- On-device Whisper (higher accuracy offline STT)
- Google Play distribution (if ToS resolved)
- Real-time TTS injection (if Android adds virtual audio device support)

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Minimum Android version | API 29 (Android 10) |
| Total pipeline latency (Vosk) | ~400-500ms from sentence end to avatar start |
| Total pipeline latency (cloud STT) | ~800ms-1.2s from sentence end to avatar start |
| Avatar framerate (audio mode) | 30fps on Snapdragon 600 series |
| Avatar framerate (video mode) | 30fps 2D sprites on Snapdragon 600 series |
| Overlay memory footprint | < 100MB RAM |
| Dictionary size (on-device) | < 15MB |
| APK size | < 40MB (models downloaded on first launch) |
| Total on-device after setup | < 120MB |
| Battery drain (active call) | < 30% additional vs Telegram alone |

---

## Phases

| Phase | Focus | Deliverable |
|-------|-------|-------------|
| **0 — Validation** | Test AudioPlaybackCapture with Telegram on Android 10-14. Determine Path A viability. Repo setup, project structure, contract test fixtures. | Go/no-go on Path A. Buildable skeleton. Shared test fixtures. |
| **1 — Audio + STT** | AudioPlaybackCapture or bot relay working. Silero VAD + Vosk STT on-device. Subtitle display. | Audio → text working during a live Telegram call |
| **2 — Avatar** | 3D model renders on Android overlay, plays quaternion keyframe animations. 2D sprite fallback for video mode. IK pipeline for MediaPipe→quaternion conversion. | Avatar signs from local test data |
| **3 — Dictionary + Fingerspelling** | MediaPipe pipeline extracts signs → IK → quaternions. 50 seed signs + fingerspelling. Quality validation (score 3+). Begin expansion toward 500. | Working dictionary. Dictionary pipeline runs continuously. |
| **4 — ASL Translation** | 3-tier engine: pattern hash table, MiniLM + FAISS vector similarity, small model (if data sufficient). | English → ASL gloss working. Contract tests passing. |
| **5 — Integration** | Full pipeline: audio → VAD → STT → ASL translation → signs → overlay avatar + subtitles + confidence | End-to-end working prototype. Integration tests passing. |
| **6 — Polish** | Captions fallback, quick phrases (Telegram messages), settings, always-ready mode, battery saver, error handling, confidence indicator | Usable by real users |
| **7 — User Testing** | Recruit ASL users, gather feedback, iterate on sign quality and readability | Validated product |

Dictionary expansion (50→500 signs) runs continuously from Phase 3 through Phase 7.

---

## 5 Parallel Workstreams

### Agent 1a — Rendering Engine
- Kotlin
- OpenGL ES 3D avatar renderer (audio call mode)
- 2D sprite avatar renderer (video call mode)
- GLTF model loading
- Quaternion-based keyframe animation system
- Slerp interpolation + transition path playback
- IK solver (MediaPipe positions → bone quaternions, used at dictionary build time)
- Confidence indicator (border glow system)
- Performance profiling and optimization for Snapdragon 600

### Agent 1b — Android App Shell
- Kotlin
- SYSTEM_ALERT_WINDOW overlay service
- AudioPlaybackCapture integration (Path A)
- MediaProjection handling + "always ready" mode
- Overlay UI (audio mode, video mode, subtitle bar, quick phrases)
- Settings + setup flow
- Vosk STT integration (on-device)
- Silero VAD integration (on-device)
- Optional cloud STT client (Groq / Deepgram / Google)
- Battery saver mode
- Model download on first launch (Vosk + MiniLM)
- Integrates with Agent 1a renderer as a library/module

### Agent 2 — Bot Relay (Path B Fallback)
- Python
- Telegram bot (python-telegram-bot + tgcalls)
- Audio streaming to phone over WebSocket
- Minimal REST endpoints (session start/end)
- Designed to be optional — app works without it if Path A succeeds
- Documentation: self-hosting instructions for the community

### Agent 3 — Sign Dictionary Pipeline
- Python
- MediaPipe hand/pose/face extraction from video
- IK solver: MediaPipe landmarks → bone quaternion keyframes
- Open dataset ingestion (each source license-verified individually)
- Keyframe extraction, normalization, and quality validation
- Sign transition extraction for common pairs
- Dictionary builder → binary + JSON output
- Quality validation framework (readability scoring, render regression tests)
- 26 fingerspelling shapes (A-Z)
- 10 number signs (0-9)
- 50 seed signs → continuous expansion to 500 (quality over quantity)

### Agent 4 — ASL Translation Engine
- Python (training/data) → ONNX (on-device inference)
- Scrape English ↔ ASL parallel data (legal sources only, each verified)
- Build pattern hash table with template slots (few thousand patterns)
- Integrate MiniLM-L6 for sentence embedding
- Build FAISS product-quantized index for similarity matching
- Implement slot adaptation for approximate matches
- If sufficient data: train T5-small on English → ASL gloss (< 20MB ONNX, INT8)
- If insufficient data: ship V1 with tiers 1+2 only
- Export all artifacts for Android: hash table, FAISS index, ONNX models
- Deliver: artifacts, evaluation metrics, contract test fixtures
