package engine

import "fmt"

// STTOutput matches the spec's STT Output contract.
type STTOutput struct {
	Sentence   string  `json:"sentence"`
	Confidence float64 `json:"confidence"`
	Source     string  `json:"source"`
}

// TranslationOutput matches the spec's ASL Translation Engine Output contract.
type TranslationOutput struct {
	ASLGloss   []string `json:"asl_gloss"`
	Method     string   `json:"method"`
	Pattern    string   `json:"pattern,omitempty"`
	Confidence float64  `json:"confidence"`
}

// SignType distinguishes regular signs from fingerspelled words.
type SignType string

const (
	SignTypeSign        SignType = "sign"
	SignTypeFingerSpell SignType = "fingerspell"
)

// SignEntry represents a single sign in the output sequence.
type SignEntry struct {
	Gloss      string   `json:"gloss"`
	Type       SignType  `json:"type"`
	SignID     string   `json:"sign_id,omitempty"`
	Letters    []string `json:"letters,omitempty"`
	DurationMs int      `json:"duration_ms"`
}

// SignSequence is the full pipeline output matching the spec contract.
type SignSequence struct {
	Type               string      `json:"type"`
	English            string      `json:"english"`
	PipelineConfidence float64     `json:"pipeline_confidence"`
	Gloss              []string    `json:"gloss"`
	Signs              []SignEntry `json:"signs"`
}

// StatusState represents pipeline status.
type StatusState string

const (
	StatusListening  StatusState = "listening"
	StatusProcessing StatusState = "processing"
	StatusSigning    StatusState = "signing"
	StatusError      StatusState = "error"
)

// StatusEvent represents a pipeline status event.
type StatusEvent struct {
	Type               string     `json:"type"`
	State              StatusState `json:"state"`
	PipelineConfidence float64    `json:"pipeline_confidence,omitempty"`
	Fallback           string     `json:"fallback,omitempty"`
	Text               string     `json:"text,omitempty"`
}

// LowConfidenceError is returned when STT confidence is below threshold.
type LowConfidenceError struct {
	Sentence   string
	Confidence float64
	Threshold  float64
}

func (e *LowConfidenceError) Error() string {
	return fmt.Sprintf("stt confidence %.2f below threshold %.2f: %s",
		e.Confidence, e.Threshold, e.Sentence)
}
