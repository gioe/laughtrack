import Foundation

#if canImport(UserNotifications)
import UserNotifications
#endif

#if canImport(UIKit)
import UIKit
#endif

public enum PushAuthorizationStatus: Sendable, Equatable {
    case notDetermined
    case authorized
    case denied
}

public protocol PushAuthorizationStatusProviding: Sendable {
    func currentAuthorizationStatus() async -> PushAuthorizationStatus
}

public protocol PushAuthorizationRequesting: Sendable {
    func requestAuthorization() async -> Bool
}

public protocol SystemSettingsOpening: Sendable {
    @MainActor func openAppSystemSettings()
}

public struct SystemPushAuthorizationStatusProvider: PushAuthorizationStatusProviding {
    public init() {}

    public func currentAuthorizationStatus() async -> PushAuthorizationStatus {
        #if canImport(UserNotifications)
        let raw = await UNUserNotificationCenter.current().notificationSettings().authorizationStatus
        switch raw {
        case .notDetermined:
            return .notDetermined
        case .authorized, .provisional, .ephemeral:
            return .authorized
        case .denied:
            return .denied
        @unknown default:
            // Conservative fallback: treat unrecognized future cases as denied so the
            // user gets the explanatory Open Settings alert rather than a silent no-op
            // or an infinite re-prompt loop until we explicitly handle the new case.
            return .denied
        }
        #else
        return .denied
        #endif
    }
}

public struct SystemPushAuthorizationRequester: PushAuthorizationRequesting {
    public init() {}

    public func requestAuthorization() async -> Bool {
        #if canImport(UserNotifications)
        do {
            return try await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .sound, .badge])
        } catch {
            return false
        }
        #else
        return false
        #endif
    }
}

public struct SystemSettingsOpener: SystemSettingsOpening {
    public init() {}

    @MainActor
    public func openAppSystemSettings() {
        #if canImport(UIKit)
        guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
        UIApplication.shared.open(url)
        #endif
    }
}
