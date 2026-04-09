package engine

import (
	"regexp"
	"strings"
)

var contractions = map[string]string{
	"don't":     "do not",
	"doesn't":   "does not",
	"didn't":    "did not",
	"can't":     "can not",
	"cannot":    "can not",
	"won't":     "will not",
	"wouldn't":  "would not",
	"couldn't":  "could not",
	"shouldn't": "should not",
	"isn't":     "is not",
	"aren't":    "are not",
	"wasn't":    "was not",
	"weren't":   "were not",
	"haven't":   "have not",
	"hasn't":    "has not",
	"hadn't":    "had not",
	"i'm":       "i am",
	"i've":      "i have",
	"i'll":      "i will",
	"i'd":       "i would",
	"you're":    "you are",
	"you've":    "you have",
	"you'll":    "you will",
	"you'd":     "you would",
	"he's":      "he is",
	"she's":     "she is",
	"it's":      "it is",
	"we're":     "we are",
	"we've":     "we have",
	"we'll":     "we will",
	"they're":   "they are",
	"they've":   "they have",
	"they'll":   "they will",
	"that's":    "that is",
	"what's":    "what is",
	"where's":   "where is",
	"who's":     "who is",
	"how's":     "how is",
	"there's":   "there is",
	"here's":    "here is",
	"let's":     "let us",
	"gonna":     "going to",
	"wanna":     "want to",
	"gotta":     "got to",
}

// normalize lowercases, expands contractions, strips trailing punctuation,
// and collapses whitespace. Both patterns and input go through this.
func normalize(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	s = expandContractions(s)
	s = strings.TrimRight(s, ".!?,;:")
	return strings.Join(strings.Fields(s), " ")
}

func expandContractions(s string) string {
	words := strings.Fields(s)
	var out []string
	for _, w := range words {
		if exp, ok := contractions[w]; ok {
			out = append(out, exp)
		} else {
			out = append(out, w)
		}
	}
	return strings.Join(out, " ")
}

var slotTokenRe = regexp.MustCompile(`\{(\w+)\}`)

// fillASLTemplate replaces {SLOT} markers in the ASL template with slot values
// and splits the result into gloss tokens. Multi-word slot values become
// multiple tokens.
func fillASLTemplate(template string, slots map[string]string) []string {
	filled := slotTokenRe.ReplaceAllStringFunc(template, func(m string) string {
		name := m[1 : len(m)-1]
		if v, ok := slots[name]; ok {
			return strings.ToUpper(v)
		}
		return strings.ToUpper(m)
	})
	return strings.Fields(filled)
}

// buildSlotRegex converts a pattern template like "I gave {PERSON} the {OBJECT}"
// into a compiled regex with named capture groups, returning the regex and slot names.
// Returns nil, nil if the pattern has no slots.
func buildSlotRegex(pattern string) (*regexp.Regexp, []string) {
	matches := slotTokenRe.FindAllStringSubmatch(pattern, -1)
	if len(matches) == 0 {
		return nil, nil
	}

	var names []string
	for _, m := range matches {
		names = append(names, m[1])
	}

	// Replace slots with unique placeholders before normalization
	text := pattern
	for i, name := range names {
		text = strings.Replace(text, "{"+name+"}", placeholderFor(i), 1)
	}

	// Normalize the pattern text (same transform applied to input)
	text = normalize(text)

	// Escape for regex, then swap placeholders for capture groups
	text = regexp.QuoteMeta(text)
	for i, name := range names {
		ph := strings.ToLower(placeholderFor(i))
		text = strings.Replace(text, ph, "(?P<"+name+">.+?)", 1)
	}

	re, err := regexp.Compile("^" + text + "$")
	if err != nil {
		return nil, nil
	}
	return re, names
}

func placeholderFor(i int) string {
	return "__XSLOT" + string(rune('A'+i)) + "__"
}
