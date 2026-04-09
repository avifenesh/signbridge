# ASL Translation Data Sources

Each source must be individually verified before inclusion.
This file tracks verification status, license, and usage notes.

---

## ASLG-PC12

- **Full name:** American Sign Language Parsed Corpus (ASLG-PC12)
- **Authors:** Othman & Jemni (2012)
- **License:** Research/academic use — contact authors for distribution rights
- **URL:** http://www.achrafothman.net/site/asl-sgd.php
- **Content:** ~87,000 English–ASL gloss parallel sentences
- **Quality:** Moderate — auto-generated gloss, not native-signer validated
- **Status:** PENDING VERIFICATION — do not include until license confirmed
- **Notes:**
  - Glosses use non-standard notation in some entries
  - Pre-filter: drop sentences > 20 words (long-tail, low quality)
  - Post-filter: normalize gloss tokens (uppercase, strip punctuation)

---

## NCSLGR (National Center for Sign Language and Gesture Resources)

- **URL:** https://www.bu.edu/asllrp/ncslgr.html
- **License:** Academic / research, free for non-commercial use
- **Content:** Video corpus with aligned transcripts and gloss annotations
- **Status:** PENDING VERIFICATION
- **Notes:**
  - Primarily video — gloss extraction requires alignment parsing
  - Useful for transition data (Agent 3), less so for text translation
  - Small parallel text corpus available separately

---

## ASL-LEX 2.0

- **URL:** https://asl-lex.org/
- **License:** Creative Commons Attribution 4.0 (CC BY 4.0) ✓ VERIFIED
- **Content:** Lexical database of ~2,700 ASL signs with frequency norms
- **Usage:** Sign frequency data for V1 dictionary scope (Agent 3 primary)
- **Translation usage:** Word frequency weights for Tier 1 pattern prioritization
- **Status:** APPROVED — CC BY 4.0

---

## Synthetic Augmentation (Internal)

- **Source:** Tier 1 patterns + slot filling with common English words
- **License:** Original work — no restrictions
- **Content:** ~600 example sentences (from `patterns.py` augmented field)
- **Status:** APPROVED — internal generation
- **Notes:**
  - Primary source for Tier 2 FAISS index in V1
  - Quality: high (hand-curated ASL glosses)
  - Scale: limited — 600 examples covers common conversational ASL well

---

## Gallaudet University Resources

- **URL:** https://www.gallaudet.edu/
- **Status:** PENDING INQUIRY — contact for research data sharing
- **Notes:** Potential source of validated native-signer parallel data

---

## Data Quality Checklist (per source)

Before adding any source to the training pipeline:

- [ ] License explicitly permits research/commercial use or contacted for permission
- [ ] License recorded in this file with URL and date verified
- [ ] Gloss notation normalized (uppercase, hyphenated compounds: GIVE-YOU)
- [ ] Minimum length filter applied (≥ 3 tokens)
- [ ] Maximum length filter applied (≤ 20 tokens)
- [ ] Deduplication applied (exact string match on English side)
- [ ] Sample manually reviewed by ASL-knowledgeable person (or ASL consultant)

---

## Data Format (JSONL, one record per line)

```json
{"english": "I gave you the book", "asl": "BOOK I GIVE-YOU", "source": "aslg_pc12", "confidence": 0.8}
```

Fields:
- `english`: normalized English sentence (lowercase)
- `asl`: space-separated ASL gloss tokens (uppercase)
- `source`: dataset identifier
- `confidence`: quality estimate (1.0 = validated, 0.8 = auto-generated, 0.5 = uncertain)
