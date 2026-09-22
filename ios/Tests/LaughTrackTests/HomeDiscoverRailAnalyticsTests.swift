import Testing
import LaughTrackCore

@Suite("Home Discover rail analytics")
struct HomeDiscoverRailAnalyticsTests {
    @Test("performance recorder excludes identifiers and refuses unbounded categories")
    func performancePrivacy() {
        let values: [String: Any] = ["source": "network", "account": "anonymous", "first_content_ms": 1.0,
            "server_feed_total_ms": 12.5, "client_load_ms": 10.0, "zip": "10012", "userId": "private", "token": "secret"]
        #expect(DiscoverPerformanceMetrics.safeParameters(values)?.count == 5)
        #expect(DiscoverPerformanceMetrics.safeParameters(["source": "10012", "account": "anonymous", "first_content_ms": 1.0]) == nil)
        #expect(DiscoverPerformanceMetrics.safeParameters(["source": "persisted_cache", "account": "anonymous", "first_content_ms": 1.0, "server_feed_total_ms": 12.5])?.count == 3)
    }

    @Test("server timing accepts only fixed finite bounded metrics")
    func safeServerTiming() {
        let values = DiscoverPerformanceMetrics.parse("feed_total;dur=12.5, touring;dur=120000, auth;dur=-1, policy;dur=nan, hero;dur=inf, fresh;dur=120001, secret_zip;dur=10012")
        #expect(values == ["server_feed_total_ms": 12.5, "server_touring_ms": 120000])
        #expect(DiscoverPerformanceMetrics.parse(nil).isEmpty)
        #expect(DiscoverPerformanceMetrics.parse(String(repeating: "x", count: 4097)).isEmpty)
        #expect(DiscoverPerformanceMetrics.providers.count == 16)
    }

    @Test("rail interaction analytics include policy assignment metadata")
    func railInteractionAnalyticsIncludePolicyAssignmentMetadata() {
        let parameters = DiscoverAnalyticsEvents.parameters(
            railKey: "just_passing_through",
            policyVersion: 7,
            rank: 2
        )

        #expect(DiscoverAnalyticsEvents.railSelected == "discover_rail_selected")
        #expect(parameters[DiscoverAnalyticsEvents.Param.railKey] as? String == "just_passing_through")
        #expect(parameters[DiscoverAnalyticsEvents.Param.policyVersion] as? Int == 7)
        #expect(parameters[DiscoverAnalyticsEvents.Param.rank] as? Int == 2)
    }
}
