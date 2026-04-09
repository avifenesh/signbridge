package engine

import (
	"encoding/json"
	"os"
	"strings"
)

// SignInfo holds metadata for a known sign. The actual bone keyframes
// are Agent 3's artifact; Agent 4 only needs IDs and durations.
type SignInfo struct {
	SignID     string `json:"sign_id"`
	Gloss     string `json:"gloss"`
	DurationMs int   `json:"duration_ms"`
	Category  string `json:"category"`
}

// SignDictionary maps uppercase gloss tokens to sign metadata.
type SignDictionary struct {
	signs map[string]SignInfo
}

// LoadDictionary reads sign metadata from a JSON file.
// Returns an empty (usable) dictionary if the file is missing or invalid.
func LoadDictionary(path string) *SignDictionary {
	d := &SignDictionary{signs: make(map[string]SignInfo)}
	if path == "" {
		return d
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return d
	}
	var raw map[string]SignInfo
	if err := json.Unmarshal(data, &raw); err != nil {
		return d
	}
	for k, v := range raw {
		d.signs[strings.ToUpper(k)] = v
	}
	return d
}

// Lookup finds sign metadata by gloss. Returns false if unknown.
func (d *SignDictionary) Lookup(gloss string) (SignEntry, bool) {
	info, ok := d.signs[strings.ToUpper(gloss)]
	if !ok {
		return SignEntry{}, false
	}
	return SignEntry{
		Gloss:      info.Gloss,
		Type:       SignTypeSign,
		SignID:     info.SignID,
		DurationMs: info.DurationMs,
	}, true
}

// Size returns the number of entries in the dictionary.
func (d *SignDictionary) Size() int {
	return len(d.signs)
}
