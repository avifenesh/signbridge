package engine

import (
	"fmt"
	"strings"
)

// Config configures the translation engine.
type Config struct {
	PatternsPath     string   // required: path to patterns.json
	DictionaryPath   string   // optional: path to dictionary.json
	Embedder         Embedder // optional: defaults to BagOfWordsEmbedder(384)
	Tier2Threshold   float64  // optional: defaults to 0.75
	MinSTTConfidence float64  // optional: defaults to 0.3
}

// Engine is the 3-tier ASL translation engine.
type Engine struct {
	tier1            *Tier1
	tier2            *Tier2
	tier3            *Tier3
	dict             *SignDictionary
	minSTTConfidence float64
}

// New creates an Engine from the given configuration.
func New(cfg Config) (*Engine, error) {
	t1, err := NewTier1(cfg.PatternsPath)
	if err != nil {
		return nil, fmt.Errorf("tier1: %w", err)
	}

	embedder := cfg.Embedder
	if embedder == nil {
		embedder = NewBagOfWordsEmbedder(384)
	}

	t2 := NewTier2(embedder, cfg.Tier2Threshold)

	// Index all tier1 patterns into tier2 for similarity fallback
	for _, p := range t1.patterns {
		if err := t2.AddPattern(p.Pattern, p.ASLTemplate, p.slotNames); err != nil {
			return nil, fmt.Errorf("tier2 index: %w", err)
		}
	}

	minConf := cfg.MinSTTConfidence
	if minConf <= 0 {
		minConf = 0.3
	}

	return &Engine{
		tier1:            t1,
		tier2:            t2,
		tier3:            &Tier3{},
		dict:             LoadDictionary(cfg.DictionaryPath),
		minSTTConfidence: minConf,
	}, nil
}

// Translate runs the 3-tier pipeline on STT output and returns a sign sequence.
//
// Returns LowConfidenceError if STT confidence is below threshold (caption-only mode).
// Otherwise always returns a result — falling through tiers to word-by-word if needed.
func (e *Engine) Translate(input STTOutput) (*SignSequence, error) {
	// Gate: reject low-confidence STT (don't sign garbage)
	if input.Confidence > 0 && input.Confidence < e.minSTTConfidence {
		return nil, &LowConfidenceError{
			Sentence:   input.Sentence,
			Confidence: input.Confidence,
			Threshold:  e.minSTTConfidence,
		}
	}

	// Tier 1: pattern hash table
	if out, ok := e.tier1.Translate(input.Sentence); ok {
		return e.buildSequence(input, out), nil
	}

	// Tier 2: vector similarity
	if out, ok := e.tier2.Translate(input.Sentence); ok {
		return e.buildSequence(input, out), nil
	}

	// Tier 3: fine-tuned model (stub in V1)
	if out, ok := e.tier3.Translate(input.Sentence); ok {
		return e.buildSequence(input, out), nil
	}

	// Fallback: word-by-word (not proper ASL grammar, but no word is skipped)
	return e.fallbackTranslate(input), nil
}

func (e *Engine) buildSequence(input STTOutput, trans TranslationOutput) *SignSequence {
	sttConf := input.Confidence
	if sttConf == 0 {
		sttConf = 1.0
	}
	seq := &SignSequence{
		Type:               "sign_sequence",
		English:            input.Sentence,
		PipelineConfidence: sttConf * trans.Confidence,
		Gloss:              trans.ASLGloss,
	}
	for _, g := range trans.ASLGloss {
		seq.Signs = append(seq.Signs, e.lookupSign(g))
	}
	return seq
}

func (e *Engine) fallbackTranslate(input STTOutput) *SignSequence {
	words := strings.Fields(input.Sentence)
	gloss := make([]string, len(words))
	signs := make([]SignEntry, len(words))
	for i, w := range words {
		g := strings.ToUpper(w)
		gloss[i] = g
		signs[i] = e.lookupSign(g)
	}
	sttConf := input.Confidence
	if sttConf == 0 {
		sttConf = 1.0
	}
	return &SignSequence{
		Type:               "sign_sequence",
		English:            input.Sentence,
		PipelineConfidence: sttConf * 0.3, // low confidence fallback
		Gloss:              gloss,
		Signs:              signs,
	}
}

// lookupSign resolves a gloss token to a SignEntry via the dictionary,
// falling back to the base form of compound glosses, then to fingerspelling.
func (e *Engine) lookupSign(gloss string) SignEntry {
	if e.dict != nil {
		// Exact match
		if s, ok := e.dict.Lookup(gloss); ok {
			return s
		}
		// Compound gloss (e.g. GIVE-YOU): try base form
		if idx := strings.Index(gloss, "-"); idx > 0 {
			base := gloss[:idx]
			if s, ok := e.dict.Lookup(base); ok {
				s.Gloss = gloss // preserve full gloss
				return s
			}
		}
	}
	return Fingerspell(gloss)
}
