package com.signbridge.app.translation

import com.signbridge.app.model.TranslationMethod
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class PatternHashTableTest {

    private lateinit var table: PatternHashTable

    @Before
    fun setup() {
        table = PatternHashTable()
        table.loadDefaults()
    }

    @Test
    fun `loads default patterns`() {
        assertTrue(table.patternCount > 30)
    }

    @Test
    fun `exact match - hello`() {
        val result = table.match("hello")
        assertNotNull(result)
        assertEquals(listOf("HELLO"), result!!.glossTokens)
        assertEquals(TranslationMethod.PATTERN_HASH, result.method)
        assertEquals(1.0f, result.confidence)
    }

    @Test
    fun `exact match - how are you`() {
        val result = table.match("how are you")
        assertNotNull(result)
        assertTrue(result!!.glossTokens.contains("YOU"))
        assertTrue(result.glossTokens.contains("HOW"))
    }

    @Test
    fun `slot extraction - what is your name`() {
        val result = table.match("what is your name")
        assertNotNull(result)
        assertTrue(result!!.glossTokens.contains("YOUR"))
        assertTrue(result.glossTokens.contains("NAME"))
        assertTrue(result.glossTokens.contains("WHAT"))
    }

    @Test
    fun `slot extraction - I want pizza`() {
        val result = table.match("i want pizza")
        assertNotNull(result)
        assertTrue(result!!.glossTokens.contains("PIZZA"))
        assertTrue(result.glossTokens.contains("WANT"))
    }

    @Test
    fun `slot extraction - I gave you the book`() {
        val result = table.match("i gave you the book")
        assertNotNull(result)
        assertTrue(result!!.glossTokens.contains("BOOK"))
    }

    @Test
    fun `no match returns null`() {
        val result = table.match("supercalifragilistic")
        assertNull(result)
    }

    @Test
    fun `case insensitive matching`() {
        val result = table.match("Hello")
        assertNotNull(result)
    }

    @Test
    fun `I don't understand`() {
        val result = table.match("i don't understand")
        assertNotNull(result)
        assertTrue(result!!.glossTokens.contains("UNDERSTAND"))
        assertTrue(result.glossTokens.contains("NOT"))
    }

    @Test
    fun `thank you`() {
        val result = table.match("thank you")
        assertNotNull(result)
        assertTrue(result!!.glossTokens.contains("THANK-YOU"))
    }
}
