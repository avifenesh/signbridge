# SignBridge — Plans & Roadmap

## V1 Goal

A working Android app that a deaf person can install, connect to a relay server, and use during Telegram calls to see real-time ASL signing. Free, open source, no account required.

---

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 0 | Validation + Scaffold | ✅ Complete |
| 1 | Audio + STT | ✅ Complete (relay path) |
| 2 | Avatar Renderer | ✅ Complete (placeholder model) |
| 3 | Sign Dictionary | ✅ Complete (115 signs) |
| 4 | ASL Translation | ✅ Complete (3-tier) |
| 5 | Integration | ✅ Complete |
| 6 | Polish | ✅ Complete |
| 7 | User Testing | ⏳ Not started |

---

## Current Blockers

**1. Real device testing**
Nothing has run on a physical Android phone yet. This is the single most important next step. Need: Android phone + APK install.

**2. Relay server credentials**
The relay server needs Telegram MTProto credentials (api_id + api_hash from my.telegram.org). The site is sometimes buggy — may need to retry or use a different browser.

**3. Real 3D avatar model**
Current model is a procedural geometric placeholder. Needs a 3D artist to create the cartoon humanoid described in the spec.

---

## V1 Remaining Work (prioritized)

### P0 — Can't ship without

| Task | Owner | Effort |
|------|-------|--------|
| Test on real Android phone | Anyone | 30 min |
| Deploy relay server | Anyone with Telegram creds | 1-2 hr |
| Create real cartoon avatar GLB | 3D artist | 4-8 hr |

### P1 — High impact

| Task | Owner | Effort |
|------|-------|--------|
| ASL user validation of 115 signs | Deaf/ASL user | 2-4 hr |
| Upgrade Silero VAD (replace energy-based) | Android dev | 2-3 hr |
| Expand dictionary to 300+ signs | Anyone with ASL knowledge | Ongoing |
| Wire MiniLM fully (index already rebuilt) | Android dev | 1-2 hr |

### P2 — Quality

| Task | Owner | Effort |
|------|-------|--------|
| Sign transition animations | ASL knowledge | Ongoing |
| Performance profiling on Snapdragon 600 | Android dev | 2-4 hr |
| Release APK optimization (ProGuard) | Android dev | 1-2 hr |

---

## V2 Roadmap

- iOS app
- Hebrew Sign Language (ISL)
- WhatsApp support (if API allows)
- Custom avatar appearance (skin, clothing)
- Standalone calls (no Telegram dependency)
- On-device Whisper (higher accuracy than Vosk)
- T5-small model for Tier 3 (needs English↔ASL training data)
- Sign recognition: camera → voice (hard ML problem)
- Group call support
- Google Play distribution (if Telegram ToS resolved)

---

## Architecture Decisions Log

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and all key decisions.

Critical confirmed decision: **AudioPlaybackCapture (Path A) cannot capture Telegram voice calls** — Android OS hardcodes `USAGE_VOICE_COMMUNICATION` as non-capturable. Bot relay is the only viable path.

---

## Open Questions

| Question | Status |
|----------|--------|
| Will Telegram API allow the relay bot long-term? | Unknown — ToS risk, pursue accessibility partnership |
| Can Silero VAD run on-device at acceptable latency? | Not tested yet |
| Is 30fps achievable on Snapdragon 600 with video decode active? | Not profiled |
| How readable are the hand-authored signs to real ASL users? | Not validated |
