# SignBridge — Next Tasks

Prioritized by impact. Each task is standalone — can be done independently.

---

## P0 — Must Do Before Demo

### 1. Deploy relay server and test with a real Telegram call
**Owner:** Anyone with Telegram API credentials
**Effort:** 1-2 hours
**What:**
- Get Telegram API credentials (api_id, api_hash) from https://my.telegram.org
- Deploy `relay/` to any VPS ($5/month DigitalOcean, Fly.io, Railway)
- Set environment variables, start the server
- Verify: bot joins a Telegram call, audio streams over WebSocket

**How to test without the Android app:**
```bash
# Start relay
cd relay && uvicorn main:app --host 0.0.0.0 --port 8080

# In another terminal, test the API
curl http://localhost:8080/health
curl -X POST http://localhost:8080/session/start -H "Content-Type: application/json" -d '{"chat_id": 123}'

# Connect to WebSocket and verify audio frames arrive
# (use wscat or a simple Python script)
```

**Success criteria:** Audio frames from a real Telegram call arrive via WebSocket.

---

### 2. Install APK on a real Android phone and verify app flow
**Owner:** Anyone with an Android 10+ phone
**Effort:** 30 minutes
**What:**
- Build: `./gradlew assembleDebug`
- Transfer `app/build/outputs/apk/debug/app-debug.apk` to phone
- Install via `adb install` or file manager
- Walk through setup: grant overlay permission, grant notification permission, download Vosk model
- Enter relay server URL in setup
- Start overlay and verify it draws on top of Telegram
- Make a Telegram call and verify the full pipeline works

**Success criteria:** Avatar overlay appears on top of a Telegram call and signs something.

---

### 3. Replace procedural avatar with a real 3D model
**Owner:** 3D artist or anyone with Blender
**Effort:** 4-8 hours
**What:**
- Create a friendly cartoon humanoid in Blender (upper body: head, torso, arms, hands)
- Rig with 48 named joints (exact names listed in `tools/generate_avatar_glb.py` JOINTS array)
- Include POSITION, NORMAL, JOINTS_0, WEIGHTS_0 vertex attributes
- Export as GLB
- Place at `app/src/main/assets/models/avatar.glb`
- The renderer loads it automatically — no code changes needed

**Joint names (must match exactly):**
```
right_shoulder, right_elbow, right_wrist,
left_shoulder, left_elbow, left_wrist,
right_thumb_cmc through right_thumb_tip (4 joints),
right_index_mcp through right_index_tip (4 joints),
right_middle_mcp through right_middle_tip (4 joints),
right_ring_mcp through right_ring_tip (4 joints),
right_pinky_mcp through right_pinky_tip (4 joints),
(same for left hand — 20 joints),
spine, head
```

**Spec:** Friendly cartoon style, hands slightly larger than realistic for readability,
facial blend shapes for eyebrows and mouth.

---

## P1 — High Impact Improvements

### 4. Upgrade Tier 2 to real MiniLM embeddings
**Owner:** ML engineer
**Effort:** 2-3 hours
**What:**
- Currently Tier 2 uses BoW (bag of words) hash embeddings — functional but low accuracy
- MiniLM-L6-v2 ONNX model is downloaded during setup but not wired into Tier 2 yet
- Need to: load MiniLM ONNX in `VectorSimilarityIndex.kt` via ONNX Runtime, replace `embed()` method
- Rebuild `vector_index.json` using MiniLM instead of BoW (run `agent4/scripts/build_index.py` with model downloaded)
- This significantly improves tier 2 match quality for sentences not in the pattern hash

**Files to change:** `VectorSimilarityIndex.kt` (embed method), rebuild `vector_index.json`

---

### 5. Expand sign dictionary from 115 to 300+ signs
**Owner:** Anyone with ASL knowledge (ideal: deaf ASL user)
**Effort:** Ongoing
**What:**
- Run: `python3 -c "..."` (see HANDOVER.md) to see which glosses are missing
- Add sign functions in `dictionary/build/common_signs_extended.py`
- Each sign = list of keyframes with hand joint positions
- Rebuild dictionary and convert for app
- Priority: signs used most by the 224 translation patterns

**72 missing glosses identified** — see output of:
```python
# Analyze which glosses patterns produce but dictionary doesn't have
python3 -c "
import json, re
from collections import Counter
with open('app/src/main/assets/translation/patterns.json') as f:
    patterns = json.load(f)
with open('app/src/main/assets/dictionary/signs.json') as f:
    signs = json.load(f)
existing = set(signs.keys())
counter = Counter()
for p in patterns:
    tokens = re.sub(r'\{[^}]+\}', '', p.get('asl','')).split()
    for t in tokens:
        t = t.strip('-').upper()
        if t: counter[t] += 1
for g, c in counter.most_common(100):
    if g.lower().replace('-','_') not in existing:
        print(f'{g}: {c} uses')
"
```

---

### 6. Validate signs with ASL-fluent users
**Owner:** Anyone in the deaf community
**Effort:** 2-4 hours per review session
**What:**
- The 79 content signs are hand-authored approximations
- They need validation by someone fluent in ASL
- Quality scale: 1-5 (1=unreadable, 5=native quality), minimum 3 to ship
- Focus on: hand shape accuracy, movement dynamics, facial expressions

**How:** Render each sign on a phone, have an ASL user rate readability.

---

### 7. Add Silero VAD (replace energy-based VAD)
**Owner:** Android developer
**Effort:** 2-3 hours
**What:**
- Current VAD uses simple RMS energy thresholding — misses quiet speech, triggers on noise
- Silero VAD is a small ONNX model (~2MB) with much better accuracy
- Download from: https://github.com/snakers4/silero-vad
- Load via ONNX Runtime (already a dependency)
- Replace `VadProcessor.kt` energy calculation with Silero model inference

---

## P2 — Nice to Have

### 8. Add more Kotlin tests
**What:** Integration tests for the full pipeline (audio file → sign sequence), contract tests between dictionary format and renderer.

### 9. Add sign transition animations
**What:** `transitions.json` is empty. Some sign pairs need custom movement paths instead of default slerp interpolation. Requires ASL knowledge.

### 10. Performance profiling on real device
**What:** Measure fps, memory, battery drain during a call. The spec targets 30fps on Snapdragon 600. Profile and optimize if needed.

### 11. Proguard/R8 optimization for release APK
**What:** Debug APK is 108MB. Release with minification should be significantly smaller. Test that proguard rules preserve Vosk, ONNX Runtime, and GLTF parsing.

### 12. Merge 1200+ patterns from translation/ into app
**What:** `translation/tier1/patterns.py` has 1200+ lines of patterns. Only 224 are in the app's `patterns.json`. Merge the rest for better coverage.

---

## P3 — V2 Roadmap

- iOS app
- Hebrew Sign Language (ISL)
- WhatsApp support (if API allows)
- Custom avatar appearance (skin, clothing)
- Standalone calls (no Telegram dependency)
- On-device Whisper (higher accuracy than Vosk)
- T5-small model for Tier 3 (needs training data)
- Sign recognition: camera reads deaf person's signs → voice
- Group call support
- Google Play distribution (if Telegram ToS resolved)

---

## Environment Notes

- **Android SDK:** API 34, build tools, at `/home/ubuntu/android-sdk`
- **Java:** OpenJDK 17
- **Gradle:** 8.5 (wrapper included)
- **Python:** 3.x (for dictionary pipeline and relay server)
- **No KVM:** This cloud VM cannot run the Android emulator. Test on a real phone or a VM with nested virtualization.
- **Groq API key:** In `.env` (user needs to rotate it)
