import Foundation
import FirebaseAnalytics
import LaughTrackBridge

/// Bridges SharedKit's AnalyticsProvider protocol to Firebase Analytics.
///
/// Firebase event-naming constraints (enforced by the Firebase backend, not at
/// compile time): event and parameter names must be alphanumeric + underscore,
/// must start with a letter, and are capped at 40 characters. Values must be
/// String/Int/Double/Bool; nested dictionaries are silently dropped. The
/// `track` shape here forwards parameters through without coercion — callers
/// must already conform to the convention documented in ios/CLAUDE.md.
public final class FirebaseAnalyticsProvider: AnalyticsProvider {
    public init() {}

    public func track(_ event: AnalyticsEvent) {
        Analytics.logEvent(event.name, parameters: event.parameters)
    }

    public func trackScreen(_ name: String, parameters: [String: Any]?) {
        var merged: [String: Any] = parameters ?? [:]
        merged[AnalyticsParameterScreenName] = name
        Analytics.logEvent(AnalyticsEventScreenView, parameters: merged)
    }

    public func setUserProperty(_ value: String?, forName name: String) {
        Analytics.setUserProperty(value, forName: name)
    }

    public func setUserID(_ userID: String?) {
        Analytics.setUserID(userID)
    }

    public func reset() {
        Analytics.resetAnalyticsData()
    }
}
