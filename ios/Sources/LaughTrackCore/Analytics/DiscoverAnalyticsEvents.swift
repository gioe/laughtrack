import Foundation

/// Analytics contract for server-directed Discover interactions.
public enum DiscoverAnalyticsEvents {
    public static let railSelected = "discover_rail_selected"

    public enum Param {
        public static let railKey = "rail_key"
        public static let policyVersion = "policy_version"
        public static let rank = "rank"
    }

    public static func parameters(
        railKey: String,
        policyVersion: Int,
        rank: Int
    ) -> [String: Any] {
        [
            Param.railKey: railKey,
            Param.policyVersion: policyVersion,
            Param.rank: rank,
        ]
    }
}
