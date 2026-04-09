package engine

// Tier3 wraps a fine-tuned seq2seq model (T5-small ONNX) for English → ASL gloss.
// In V1 this is a stub — ships only if sufficient training data exists.
type Tier3 struct {
	loaded bool
}

// Translate attempts model-based translation.
// Returns false until a trained model artifact is loaded.
func (t *Tier3) Translate(sentence string) (TranslationOutput, bool) {
	if !t.loaded {
		return TranslationOutput{}, false
	}
	// Future: load ONNX model, run inference, return gloss
	return TranslationOutput{}, false
}
