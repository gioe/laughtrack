package app.laughtrack.android.core.analytics

/**
 * A single analytics event: a snake_case [name] (mirrors the iOS catalog) plus
 * optional typed [params]. Param values are restricted to the primitives Firebase
 * accepts (String/Int/Long/Double/Boolean) when marshalled to a Bundle.
 */
data class AnalyticsEvent(
    val name: String,
    val params: Map<String, Any> = emptyMap(),
)
