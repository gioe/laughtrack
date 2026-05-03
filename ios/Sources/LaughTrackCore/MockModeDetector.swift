import Foundation

/// Detects whether the app was launched in UI-test mock mode.
///
/// When `-UITestMockMode` is passed as a launch argument, the app should
/// pre-populate state required for App Store screenshot capture (saved
/// nearby ZIP, etc.) so screenshots are deterministic and not dependent
/// on the runner's IP-based geolocation.
///
/// Usage from a UI test:
/// ```swift
/// app.launchArguments.append("-UITestMockMode")
/// app.launch()
/// ```
public enum MockModeDetector {
    public static let mockModeArgument = "-UITestMockMode"

    /// True when the app was launched with `-UITestMockMode`.
    public static var isMockMode: Bool {
        ProcessInfo.processInfo.arguments.contains(mockModeArgument)
    }
}
