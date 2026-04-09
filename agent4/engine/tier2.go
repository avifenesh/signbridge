package engine

import (
	"math"
	"strings"
)

// Embedder produces vector embeddings from text.
// In production this is backed by MiniLM-L6 via ONNX.
type Embedder interface {
	Embed(text string) ([]float32, error)
	Dims() int
}

// VectorEntry is a pattern with its pre-computed embedding.
type VectorEntry struct {
	Embedding   []float32
	Pattern     string
	ASLTemplate string
	SlotNames   []string
}

// Tier2 performs vector similarity search over embedded patterns.
type Tier2 struct {
	embedder  Embedder
	entries   []VectorEntry
	threshold float64
}

// NewTier2 creates a vector similarity engine. Threshold defaults to 0.75.
func NewTier2(embedder Embedder, threshold float64) *Tier2 {
	if threshold <= 0 {
		threshold = 0.75
	}
	return &Tier2{
		embedder:  embedder,
		threshold: threshold,
	}
}

// AddPattern embeds and indexes a pattern for later similarity search.
func (t *Tier2) AddPattern(pattern, aslTemplate string, slotNames []string) error {
	emb, err := t.embedder.Embed(pattern)
	if err != nil {
		return err
	}
	t.entries = append(t.entries, VectorEntry{
		Embedding:   emb,
		Pattern:     pattern,
		ASLTemplate: aslTemplate,
		SlotNames:   slotNames,
	})
	return nil
}

// Translate finds the nearest pattern by cosine similarity and adapts it.
// Returns false if no match exceeds the threshold.
func (t *Tier2) Translate(sentence string) (TranslationOutput, bool) {
	if len(t.entries) == 0 {
		return TranslationOutput{}, false
	}
	emb, err := t.embedder.Embed(sentence)
	if err != nil {
		return TranslationOutput{}, false
	}

	bestIdx := -1
	bestSim := float64(-1)
	for i, e := range t.entries {
		sim := cosineSimilarity(emb, e.Embedding)
		if sim > bestSim {
			bestSim = sim
			bestIdx = i
		}
	}

	if bestIdx < 0 || bestSim < t.threshold {
		return TranslationOutput{}, false
	}

	best := t.entries[bestIdx]
	gloss := adaptTemplate(best.ASLTemplate, best.Pattern, best.SlotNames, sentence)

	return TranslationOutput{
		ASLGloss:   gloss,
		Method:     "vector_similarity",
		Pattern:    best.Pattern,
		Confidence: bestSim,
	}, true
}

// adaptTemplate fills an ASL template using slot extraction from the input.
// If the pattern has no slots or regex extraction fails, the template tokens
// are returned directly.
func adaptTemplate(aslTemplate, matchedPattern string, slotNames []string, input string) []string {
	if len(slotNames) == 0 {
		return strings.Fields(strings.ToUpper(aslTemplate))
	}

	// Try extracting slots via regex (same logic as tier1)
	re, _ := buildSlotRegex(matchedPattern)
	if re != nil {
		norm := normalize(input)
		if match := re.FindStringSubmatch(norm); match != nil {
			slots := make(map[string]string)
			for i, name := range re.SubexpNames() {
				if i > 0 && name != "" {
					slots[name] = strings.ToUpper(match[i])
				}
			}
			return fillASLTemplate(aslTemplate, slots)
		}
	}

	// Regex didn't match (approximate hit) — return template tokens without slots
	cleaned := slotTokenRe.ReplaceAllString(aslTemplate, "")
	var tokens []string
	for _, t := range strings.Fields(cleaned) {
		t = strings.Trim(t, "-")
		if t != "" {
			tokens = append(tokens, strings.ToUpper(t))
		}
	}
	return tokens
}

func cosineSimilarity(a, b []float32) float64 {
	if len(a) != len(b) {
		return 0
	}
	var dot, normA, normB float64
	for i := range a {
		dot += float64(a[i]) * float64(b[i])
		normA += float64(a[i]) * float64(a[i])
		normB += float64(b[i]) * float64(b[i])
	}
	if normA == 0 || normB == 0 {
		return 0
	}
	return dot / (math.Sqrt(normA) * math.Sqrt(normB))
}

// --- Bag-of-words embedder (built-in fallback for dev/testing) ---

// BagOfWordsEmbedder produces sparse vectors by hashing words to dimensions.
// Not suitable for production; use MiniLM-L6 ONNX for real embeddings.
type BagOfWordsEmbedder struct {
	dims int
}

// NewBagOfWordsEmbedder creates a BoW embedder with the given dimensionality.
func NewBagOfWordsEmbedder(dims int) *BagOfWordsEmbedder {
	return &BagOfWordsEmbedder{dims: dims}
}

func (e *BagOfWordsEmbedder) Dims() int { return e.dims }

func (e *BagOfWordsEmbedder) Embed(text string) ([]float32, error) {
	words := strings.Fields(strings.ToLower(text))
	vec := make([]float32, e.dims)
	for _, w := range words {
		idx := int(fnv32a(w)) % e.dims
		vec[idx] += 1.0
	}
	// L2-normalize
	var norm float64
	for _, v := range vec {
		norm += float64(v * v)
	}
	if norm > 0 {
		norm = math.Sqrt(norm)
		for i := range vec {
			vec[i] = float32(float64(vec[i]) / norm)
		}
	}
	return vec, nil
}

// fnv32a is a deterministic hash for distributing words across dimensions.
func fnv32a(s string) uint32 {
	h := uint32(2166136261)
	for i := 0; i < len(s); i++ {
		h ^= uint32(s[i])
		h *= 16777619
	}
	return h
}
