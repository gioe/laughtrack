package app.laughtrack.android.core.ui.components

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RemoteImageUrlTest {
    @Test
    fun apiRelativeArtwork_resolvesAgainstLaughTrackOrigin() {
        assertEquals(
            "https://www.laugh-track.com/api/v1/podcast-artwork?url=encoded",
            normalizeRemoteImageUrl("/api/v1/podcast-artwork?url=encoded"),
        )
    }

    @Test
    fun externalUrls_preserveAbsoluteAndNormalizeSchemeLessValues() {
        assertEquals(
            "https://cdn.example.com/art.jpg",
            normalizeRemoteImageUrl("https://cdn.example.com/art.jpg"),
        )
        assertEquals(
            "https://cdn.example.com/art.jpg",
            normalizeRemoteImageUrl("cdn.example.com/art.jpg"),
        )
        assertEquals(
            "https://cdn.example.com/art.jpg",
            normalizeRemoteImageUrl("//cdn.example.com/art.jpg"),
        )
    }

    @Test
    fun blankValues_remainMissing() {
        assertNull(normalizeRemoteImageUrl(null))
        assertNull(normalizeRemoteImageUrl("  "))
    }
}
