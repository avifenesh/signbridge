package engine

import (
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"strings"
)

// PatternEntry is a single entry in the pattern hash table.
type PatternEntry struct {
	Pattern     string `json:"pattern"`
	ASLTemplate string `json:"asl_template"`
	regex       *regexp.Regexp
	slotNames   []string
	specificity int // literal word count (more = more specific)
}

// Tier1 is the pattern hash table engine.
type Tier1 struct {
	patterns []PatternEntry
}

// NewTier1 loads patterns from a JSON file and compiles them.
func NewTier1(path string) (*Tier1, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read patterns: %w", err)
	}
	var raw []PatternEntry
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("parse patterns: %w", err)
	}
	for i := range raw {
		if err := raw[i].compile(); err != nil {
			return nil, fmt.Errorf("compile pattern %q: %w", raw[i].Pattern, err)
		}
	}
	return &Tier1{patterns: raw}, nil
}

// compile converts the template pattern into a regex with named capture groups.
func (p *PatternEntry) compile() error {
	re, names := buildSlotRegex(p.Pattern)
	if re != nil {
		p.regex = re
		p.slotNames = names
	} else {
		norm := normalize(p.Pattern)
		escaped := regexp.QuoteMeta(norm)
		compiled, err := regexp.Compile("^" + escaped + "$")
		if err != nil {
			return err
		}
		p.regex = compiled
	}
	p.specificity = len(strings.Fields(p.Pattern)) - len(p.slotNames)
	return nil
}

// Translate tries all patterns and returns the most specific match
// (highest literal word count). Returns zero value and false on no match.
func (t *Tier1) Translate(sentence string) (TranslationOutput, bool) {
	norm := normalize(sentence)
	bestSpec := -1
	var bestPattern *PatternEntry
	var bestMatch []string

	for i := range t.patterns {
		p := &t.patterns[i]
		match := p.regex.FindStringSubmatch(norm)
		if match == nil {
			continue
		}
		if p.specificity > bestSpec {
			bestSpec = p.specificity
			bestPattern = p
			bestMatch = match
		}
	}

	if bestPattern == nil {
		return TranslationOutput{}, false
	}

	slots := make(map[string]string)
	for i, name := range bestPattern.regex.SubexpNames() {
		if i > 0 && name != "" {
			slots[name] = strings.ToUpper(bestMatch[i])
		}
	}

	gloss := fillASLTemplate(bestPattern.ASLTemplate, slots)
	return TranslationOutput{
		ASLGloss:   gloss,
		Method:     "pattern_hash",
		Pattern:    bestPattern.Pattern,
		Confidence: 1.0,
	}, true
}
