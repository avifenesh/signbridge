package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"signbridge/agent4/engine"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintf(os.Stderr, "usage: translate <sentence>\n")
		os.Exit(1)
	}

	sentence := strings.Join(os.Args[1:], " ")

	eng, err := engine.New(engine.Config{
		PatternsPath:   "data/patterns.json",
		DictionaryPath: "data/dictionary.json",
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "init: %v\n", err)
		os.Exit(1)
	}

	result, err := eng.Translate(engine.STTOutput{
		Sentence:   sentence,
		Confidence: 0.95,
		Source:     "cli",
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "translate: %v\n", err)
		os.Exit(1)
	}

	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	enc.Encode(result)
}
