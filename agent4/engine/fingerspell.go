package engine

import "strings"

// Fingerspell converts a word into a fingerspelled SignEntry.
// Letters A-Z and digits 0-9 each become one letter in the sequence.
// Duration is ~300ms per letter.
func Fingerspell(word string) SignEntry {
	upper := strings.ToUpper(strings.TrimSpace(word))
	var letters []string
	for _, c := range upper {
		switch {
		case c >= 'A' && c <= 'Z':
			letters = append(letters, string(c))
		case c >= '0' && c <= '9':
			letters = append(letters, string(c))
		}
	}
	if len(letters) == 0 {
		letters = []string{upper}
	}
	return SignEntry{
		Gloss:      upper,
		Type:       SignTypeFingerSpell,
		Letters:    letters,
		DurationMs: len(letters) * 300,
	}
}
