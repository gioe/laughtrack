import Testing
import LaughTrackCore

@Suite("Home Discover rail analytics")
struct HomeDiscoverRailAnalyticsTests {
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
