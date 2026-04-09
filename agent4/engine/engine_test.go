package engine

import (
	"reflect"
	"testing"
)

const patternsPath = "../data/patterns.json"
const dictPath = "../data/dictionary.json"

func testEngine(t *testing.T) *Engine {
	t.Helper()
	eng, err := New(Config{
		PatternsPath:   patternsPath,
		DictionaryPath: dictPath,
	})
	if err != nil {
		t.Fatalf("new engine: %v", err)
	}
	return eng
}

// --- normalize ---

func TestNormalize(t *testing.T) {
	tests := []struct {
		in, want string
	}{
		{"Hello!", "hello"},
		{"  What is your name?  ", "what is your name"},
		{"I DON'T like that.", "i do not like that"},
		{"I can't believe it", "i can not believe it"},
		{"She's   here", "she is here"},
		{"I'm gonna go", "i am going to go"},
	}
	for _, tt := range tests {
		got := normalize(tt.in)
		if got != tt.want {
			t.Errorf("normalize(%q) = %q, want %q", tt.in, got, tt.want)
		}
	}
}

// --- fingerspell ---

func TestFingerspell(t *testing.T) {
	s := Fingerspell("Sarah")
	if s.Type != SignTypeFingerSpell {
		t.Errorf("type = %q, want fingerspell", s.Type)
	}
	want := []string{"S", "A", "R", "A", "H"}
	if !reflect.DeepEqual(s.Letters, want) {
		t.Errorf("letters = %v, want %v", s.Letters, want)
	}
	if s.DurationMs != 1500 {
		t.Errorf("duration = %d, want 1500", s.DurationMs)
	}
}

func TestFingerspellDigits(t *testing.T) {
	s := Fingerspell("A1B2")
	want := []string{"A", "1", "B", "2"}
	if !reflect.DeepEqual(s.Letters, want) {
		t.Errorf("letters = %v, want %v", s.Letters, want)
	}
}

// --- tier 1 ---

func TestTier1GaveYouTheBook(t *testing.T) {
	eng := testEngine(t)
	out, ok := eng.tier1.Translate("I gave you the book")
	if !ok {
		t.Fatal("expected tier1 match")
	}
	wantGloss := []string{"BOOK", "I", "GIVE-YOU"}
	if !reflect.DeepEqual(out.ASLGloss, wantGloss) {
		t.Errorf("gloss = %v, want %v", out.ASLGloss, wantGloss)
	}
	if out.Method != "pattern_hash" {
		t.Errorf("method = %q, want pattern_hash", out.Method)
	}
	if out.Confidence != 1.0 {
		t.Errorf("confidence = %f, want 1.0", out.Confidence)
	}
}

func TestTier1WhatIsYourName(t *testing.T) {
	eng := testEngine(t)
	out, ok := eng.tier1.Translate("What is your name?")
	if !ok {
		t.Fatal("expected tier1 match")
	}
	wantGloss := []string{"YOUR", "NAME", "WHAT"}
	if !reflect.DeepEqual(out.ASLGloss, wantGloss) {
		t.Errorf("gloss = %v, want %v", out.ASLGloss, wantGloss)
	}
}

func TestTier1ContractionExpansion(t *testing.T) {
	eng := testEngine(t)
	// "I don't like that" → normalized "i do not like that" → matches "I do not like {OBJECT}"
	out, ok := eng.tier1.Translate("I don't like that")
	if !ok {
		t.Fatal("expected tier1 match")
	}
	wantGloss := []string{"THAT", "I", "LIKE", "NOT"}
	if !reflect.DeepEqual(out.ASLGloss, wantGloss) {
		t.Errorf("gloss = %v, want %v", out.ASLGloss, wantGloss)
	}
}

func TestTier1NoSlots(t *testing.T) {
	eng := testEngine(t)
	out, ok := eng.tier1.Translate("Thank you")
	if !ok {
		t.Fatal("expected tier1 match for 'Thank you'")
	}
	wantGloss := []string{"THANK-YOU"}
	if !reflect.DeepEqual(out.ASLGloss, wantGloss) {
		t.Errorf("gloss = %v, want %v", out.ASLGloss, wantGloss)
	}
}

func TestTier1NoMatch(t *testing.T) {
	eng := testEngine(t)
	_, ok := eng.tier1.Translate("The quick brown fox jumps over the lazy dog")
	if ok {
		t.Error("expected no tier1 match for unrecognized sentence")
	}
}

// --- tier 2 ---

func TestTier2SimilarSentence(t *testing.T) {
	eng := testEngine(t)
	// "The weather looks nice today" is similar to pattern "The weather is nice today"
	out, ok := eng.tier2.Translate("The weather looks nice today")
	if !ok {
		t.Fatal("expected tier2 match for similar sentence")
	}
	if out.Method != "vector_similarity" {
		t.Errorf("method = %q, want vector_similarity", out.Method)
	}
	if out.Confidence < 0.75 {
		t.Errorf("confidence = %f, want >= 0.75", out.Confidence)
	}
}

func TestTier2BelowThreshold(t *testing.T) {
	eng := testEngine(t)
	// Completely unrelated sentence should not match anything
	_, ok := eng.tier2.Translate("xylophone quantum zebra")
	if ok {
		t.Error("expected no tier2 match for completely unrelated input")
	}
}

// --- full engine ---

func TestEngineTranslateTier1(t *testing.T) {
	eng := testEngine(t)
	seq, err := eng.Translate(STTOutput{
		Sentence:   "I gave you the book",
		Confidence: 0.94,
		Source:     "vosk",
	})
	if err != nil {
		t.Fatal(err)
	}
	if seq.Type != "sign_sequence" {
		t.Errorf("type = %q, want sign_sequence", seq.Type)
	}
	if seq.English != "I gave you the book" {
		t.Errorf("english = %q, want original", seq.English)
	}
	wantGloss := []string{"BOOK", "I", "GIVE-YOU"}
	if !reflect.DeepEqual(seq.Gloss, wantGloss) {
		t.Errorf("gloss = %v, want %v", seq.Gloss, wantGloss)
	}
	// BOOK should be type=sign from dictionary
	if seq.Signs[0].Type != SignTypeSign {
		t.Errorf("signs[0].type = %q, want sign", seq.Signs[0].Type)
	}
	if seq.Signs[0].SignID != "book" {
		t.Errorf("signs[0].sign_id = %q, want book", seq.Signs[0].SignID)
	}
	// GIVE-YOU should resolve via dictionary
	if seq.Signs[2].Type != SignTypeSign {
		t.Errorf("signs[2].type = %q, want sign (directional verb)", seq.Signs[2].Type)
	}
}

func TestEngineTranslateFallback(t *testing.T) {
	eng := testEngine(t)
	seq, err := eng.Translate(STTOutput{
		Sentence:   "xylophone quantum zebra",
		Confidence: 0.80,
		Source:     "vosk",
	})
	if err != nil {
		t.Fatal(err)
	}
	// Should fall through to word-by-word, all fingerspelled
	if len(seq.Signs) != 3 {
		t.Fatalf("signs count = %d, want 3", len(seq.Signs))
	}
	for _, s := range seq.Signs {
		if s.Type != SignTypeFingerSpell {
			t.Errorf("sign %q should be fingerspelled, got type %q", s.Gloss, s.Type)
		}
	}
}

func TestEngineLowConfidence(t *testing.T) {
	eng := testEngine(t)
	_, err := eng.Translate(STTOutput{
		Sentence:   "something something",
		Confidence: 0.2,
		Source:     "vosk",
	})
	if err == nil {
		t.Fatal("expected error for low STT confidence")
	}
	lcErr, ok := err.(*LowConfidenceError)
	if !ok {
		t.Fatalf("expected LowConfidenceError, got %T", err)
	}
	if lcErr.Threshold != 0.3 {
		t.Errorf("threshold = %f, want 0.3", lcErr.Threshold)
	}
}

func TestEngineZeroConfidencePassesThrough(t *testing.T) {
	eng := testEngine(t)
	// Confidence=0 means "not set" — should pass through, not error
	_, err := eng.Translate(STTOutput{
		Sentence:   "Hello",
		Confidence: 0,
		Source:     "cli",
	})
	if err != nil {
		t.Fatalf("confidence=0 should pass through, got error: %v", err)
	}
}

// --- contract test fixtures from spec ---

func TestContractSpecExamples(t *testing.T) {
	eng := testEngine(t)

	tests := []struct {
		name      string
		input     string
		wantGloss []string
		wantTier  string
	}{
		{
			name:      "spec example 1: gave book",
			input:     "I gave you the book",
			wantGloss: []string{"BOOK", "I", "GIVE-YOU"},
			wantTier:  "pattern_hash",
		},
		{
			name:      "spec example 2: your name",
			input:     "What is your name?",
			wantGloss: []string{"YOUR", "NAME", "WHAT"},
			wantTier:  "pattern_hash",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			seq, err := eng.Translate(STTOutput{
				Sentence:   tt.input,
				Confidence: 0.94,
				Source:     "test",
			})
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(seq.Gloss, tt.wantGloss) {
				t.Errorf("gloss = %v, want %v", seq.Gloss, tt.wantGloss)
			}
		})
	}
}

func TestContractOutputFormat(t *testing.T) {
	eng := testEngine(t)
	seq, err := eng.Translate(STTOutput{
		Sentence:   "I gave you the book",
		Confidence: 0.94,
		Source:     "vosk",
	})
	if err != nil {
		t.Fatal(err)
	}

	// Verify all required fields per spec contract
	if seq.Type != "sign_sequence" {
		t.Errorf("type = %q", seq.Type)
	}
	if seq.PipelineConfidence <= 0 || seq.PipelineConfidence > 1.0 {
		t.Errorf("pipeline_confidence = %f, want (0, 1]", seq.PipelineConfidence)
	}
	if len(seq.Gloss) == 0 {
		t.Error("gloss is empty")
	}
	if len(seq.Signs) == 0 {
		t.Error("signs is empty")
	}
	for i, s := range seq.Signs {
		if s.Gloss == "" {
			t.Errorf("signs[%d].gloss is empty", i)
		}
		if s.Type != SignTypeSign && s.Type != SignTypeFingerSpell {
			t.Errorf("signs[%d].type = %q, want sign or fingerspell", i, s.Type)
		}
		if s.DurationMs <= 0 {
			t.Errorf("signs[%d].duration_ms = %d, want > 0", i, s.DurationMs)
		}
	}
}

// --- dictionary ---

func TestDictionaryLookup(t *testing.T) {
	d := LoadDictionary(dictPath)
	if d.Size() == 0 {
		t.Fatal("dictionary is empty")
	}

	s, ok := d.Lookup("BOOK")
	if !ok {
		t.Fatal("BOOK not found in dictionary")
	}
	if s.SignID != "book" {
		t.Errorf("sign_id = %q, want book", s.SignID)
	}
	if s.DurationMs != 600 {
		t.Errorf("duration = %d, want 600", s.DurationMs)
	}
}

func TestDictionaryMissing(t *testing.T) {
	d := LoadDictionary("")
	_, ok := d.Lookup("ANYTHING")
	if ok {
		t.Error("empty dictionary should not find anything")
	}
}

func TestDictionaryCaseInsensitive(t *testing.T) {
	d := LoadDictionary(dictPath)
	_, ok := d.Lookup("book")
	if !ok {
		t.Error("dictionary lookup should be case-insensitive")
	}
}
