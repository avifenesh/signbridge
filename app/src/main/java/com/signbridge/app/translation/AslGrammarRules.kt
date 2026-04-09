package com.signbridge.app.translation

/**
 * Rule-based English → ASL gloss grammar transformation.
 *
 * ASL grammar differs from English:
 *   - Topic-comment: topic comes first ("BOOK, I GIVE-YOU")
 *   - WH-questions end with question word ("YOUR NAME WHAT")
 *   - Negation follows the verb ("UNDERSTAND I NOT")
 *   - Time references come first ("YESTERDAY I GO STORE")
 *   - No copula ("be" is dropped)
 *   - No articles (a, an, the are dropped)
 *   - Directional verbs incorporate subject/object ("GIVE-YOU")
 *
 * Used as the fallback path when tiers 1-3 all miss.
 * Better than word-by-word SEE order: produces approximate ASL grammar.
 */
object AslGrammarRules {

    private val DROP_WORDS = setOf(
        "a", "an", "the", "is", "am", "are", "was", "were", "be", "been", "being",
        "do", "does", "did", "to", "it", "very", "really", "just", "quite"
    )

    private val PRONOUN_MAP = mapOf(
        "i" to "I", "me" to "I", "my" to "MY", "mine" to "MY", "myself" to "I",
        "you" to "YOU", "your" to "YOUR", "yours" to "YOUR", "yourself" to "YOU",
        "he" to "HE", "him" to "HE", "his" to "HIS",
        "she" to "SHE", "her" to "HER", "hers" to "HER",
        "we" to "WE", "us" to "WE", "our" to "OUR",
        "they" to "THEY", "them" to "THEY", "their" to "THEIR",
        "this" to "THIS", "that" to "THAT", "these" to "THESE", "those" to "THOSE"
    )

    private val CONTRACTIONS = mapOf(
        "i'm" to "i am", "i've" to "i have", "i'll" to "i will", "i'd" to "i would",
        "you're" to "you are", "you've" to "you have", "you'll" to "you will",
        "he's" to "he is", "she's" to "she is", "it's" to "it is",
        "we're" to "we are", "we've" to "we have", "we'll" to "we will",
        "they're" to "they are", "they've" to "they have", "they'll" to "they will",
        "that's" to "that is", "there's" to "there is",
        "what's" to "what is", "who's" to "who is", "where's" to "where is",
        "can't" to "can not", "won't" to "will not",
        "don't" to "do not", "doesn't" to "does not", "didn't" to "did not",
        "isn't" to "is not", "aren't" to "are not",
        "wasn't" to "was not", "weren't" to "were not",
        "haven't" to "have not", "hasn't" to "has not",
        "wouldn't" to "would not", "couldn't" to "could not", "shouldn't" to "should not",
        "let's" to "let us"
    )

    private val NEGATION_WORDS = setOf("not", "no", "never", "nothing", "nobody", "nowhere")

    private val WH_WORDS = setOf("what", "who", "where", "when", "why", "how", "which")

    private val TIME_WORDS = setOf(
        "yesterday", "today", "tomorrow", "now", "later", "before", "after",
        "already", "recently", "soon", "always", "sometimes", "often", "never",
        "morning", "afternoon", "evening", "night", "last", "next", "every",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    )

    private val DIRECTIONAL_VERBS = mapOf(
        "give" to "GIVE", "tell" to "TELL", "ask" to "ASK", "show" to "SHOW",
        "send" to "SEND", "pay" to "PAY", "help" to "HELP", "teach" to "TEACH"
    )

    /**
     * Transform an English sentence into ASL gloss order using grammar rules.
     *
     * @return List of ASL gloss tokens in approximate ASL grammar order.
     */
    fun apply(english: String): List<String> {
        val expanded = expandContractions(english.lowercase())
        val tokens = expanded.replace(Regex("[^\\w\\s'-]"), "").split("\\s+".toRegex())
            .filter { it.isNotBlank() }

        if (tokens.isEmpty()) return listOf(english.uppercase())

        val timeTokens = mutableListOf<String>()
        val whTokens = mutableListOf<String>()
        val negationTokens = mutableListOf<String>()
        val contentTokens = mutableListOf<String>()

        var i = 0
        while (i < tokens.size) {
            val word = tokens[i]

            when {
                word in DROP_WORDS -> { i++; continue }

                word in TIME_WORDS -> {
                    timeTokens.add(word.uppercase())
                    i++; continue
                }

                word in WH_WORDS -> {
                    whTokens.add(word.uppercase())
                    i++; continue
                }

                word in NEGATION_WORDS -> {
                    negationTokens.add(if (word == "not") "NOT" else word.uppercase())
                    i++; continue
                }

                word in PRONOUN_MAP -> {
                    contentTokens.add(PRONOUN_MAP[word]!!)
                    i++; continue
                }

                word in DIRECTIONAL_VERBS && i + 1 < tokens.size -> {
                    val next = tokens[i + 1]
                    val target = PRONOUN_MAP[next]
                    if (target != null) {
                        contentTokens.add("${DIRECTIONAL_VERBS[word]}-$target")
                        i += 2; continue
                    }
                    contentTokens.add(word.uppercase())
                    i++; continue
                }

                else -> {
                    contentTokens.add(word.uppercase())
                    i++
                }
            }
        }

        // ASL order: TIME + CONTENT + NEGATION + WH-QUESTION
        val gloss = timeTokens + contentTokens + negationTokens + whTokens
        return gloss.ifEmpty { listOf(english.uppercase()) }
    }

    private fun expandContractions(text: String): String {
        val words = text.split("\\s+".toRegex())
        return words.joinToString(" ") { word ->
            val clean = word.trim('.', ',', '!', '?', ';', ':')
            CONTRACTIONS[clean]?.let { expanded ->
                word.replace(clean, expanded)
            } ?: word
        }
    }
}
