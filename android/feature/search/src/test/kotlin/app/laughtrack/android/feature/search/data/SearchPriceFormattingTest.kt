package app.laughtrack.android.feature.search.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.math.BigDecimal

class SearchPriceFormattingTest {
    @Test
    fun `multiple prices expose only the cheapest ticket price`() {
        assertEquals(
            "$20",
            formatSearchPrice(listOf(BigDecimal("35"), BigDecimal("20"))),
        )
    }

    @Test
    fun `free is preserved as the cheapest ticket price`() {
        assertEquals(
            "Free",
            formatSearchPrice(listOf(BigDecimal("25"), BigDecimal.ZERO)),
        )
    }

    @Test
    fun `missing prices have no label`() {
        assertNull(formatSearchPrice(null))
    }
}
