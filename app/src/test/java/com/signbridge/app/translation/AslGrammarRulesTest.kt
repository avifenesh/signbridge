package com.signbridge.app.translation

import org.junit.Assert.*
import org.junit.Test

class AslGrammarRulesTest {

    @Test
    fun `drops articles`() {
        val result = AslGrammarRules.apply("the book")
        assertFalse(result.contains("THE"))
        assertTrue(result.contains("BOOK"))
    }

    @Test
    fun `drops copula`() {
        val result = AslGrammarRules.apply("she is happy")
        assertFalse(result.contains("IS"))
        assertTrue(result.contains("SHE"))
        assertTrue(result.contains("HAPPY"))
    }

    @Test
    fun `WH-question word moves to end`() {
        val result = AslGrammarRules.apply("what is your name")
        assertEquals("WHAT", result.last())
    }

    @Test
    fun `negation moves after content`() {
        val result = AslGrammarRules.apply("I don't understand")
        val notIdx = result.indexOf("NOT")
        val understandIdx = result.indexOf("UNDERSTAND")
        assertTrue("NOT should come after UNDERSTAND", notIdx > understandIdx)
    }

    @Test
    fun `time reference moves to front`() {
        val result = AslGrammarRules.apply("I went to the store yesterday")
        assertEquals("YESTERDAY", result.first())
    }

    @Test
    fun `expands contractions`() {
        val result = AslGrammarRules.apply("I can't go")
        assertTrue(result.contains("NOT"))
        assertTrue(result.contains("GO"))
    }

    @Test
    fun `maps pronouns`() {
        val result = AslGrammarRules.apply("he gave me the book")
        assertTrue(result.contains("HE"))
        assertTrue(result.contains("I")) // "me" → "I" in ASL
    }

    @Test
    fun `directional verb give you`() {
        val result = AslGrammarRules.apply("I give you something")
        assertTrue(result.any { it.contains("GIVE-YOU") })
    }

    @Test
    fun `directional verb tell her`() {
        val result = AslGrammarRules.apply("I tell her the news")
        assertTrue(result.any { it.contains("TELL-HER") })
    }

    @Test
    fun `empty input returns uppercase`() {
        val result = AslGrammarRules.apply("")
        assertEquals(1, result.size)
    }

    @Test
    fun `multiple time words all move to front`() {
        val result = AslGrammarRules.apply("tomorrow morning I go")
        assertEquals("TOMORROW", result[0])
        assertEquals("MORNING", result[1])
    }

    @Test
    fun `how are you`() {
        val result = AslGrammarRules.apply("how are you")
        assertTrue(result.contains("YOU"))
        assertEquals("HOW", result.last()) // WH-word at end
    }

    @Test
    fun `where is the bathroom`() {
        val result = AslGrammarRules.apply("where is the bathroom")
        assertTrue(result.contains("BATHROOM"))
        assertEquals("WHERE", result.last())
        assertFalse(result.contains("THE"))
        assertFalse(result.contains("IS"))
    }

    @Test
    fun `I am deaf`() {
        val result = AslGrammarRules.apply("I am deaf")
        assertTrue(result.contains("I"))
        assertTrue(result.contains("DEAF"))
        assertFalse(result.contains("AM"))
    }

    @Test
    fun `what time is it`() {
        val result = AslGrammarRules.apply("what time is it")
        assertTrue(result.contains("TIME"))
        assertEquals("WHAT", result.last())
    }
}
