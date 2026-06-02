import Combine
import Foundation
import LaughTrackBridge

public struct PushPermissionState: Codable, Equatable, Sendable {
    public var deferralCount: Int
    public var lastDeferredAt: Date?
    public var postOnboardingFavoriteCount: Int

    public init(
        deferralCount: Int = 0,
        lastDeferredAt: Date? = nil,
        postOnboardingFavoriteCount: Int = 0
    ) {
        self.deferralCount = deferralCount
        self.lastDeferredAt = lastDeferredAt
        self.postOnboardingFavoriteCount = postOnboardingFavoriteCount
    }

    public static let `default` = PushPermissionState()
}

@MainActor
public final class PushPermissionStateStore: ObservableObject {
    @Published public private(set) var state: PushPermissionState

    private let appStateStorage: AppStateStorageProtocol
    private let now: () -> Date

    public convenience init() {
        self.init(appStateStorage: AppStateStorage())
    }

    public init(
        appStateStorage: AppStateStorageProtocol,
        now: @escaping () -> Date = { Date() }
    ) {
        self.appStateStorage = appStateStorage
        self.now = now
        self.state = appStateStorage.getValue(
            forKey: StorageKey.state,
            as: PushPermissionState.self
        ) ?? .default
    }

    public var deferralCount: Int { state.deferralCount }
    public var lastDeferredAt: Date? { state.lastDeferredAt }
    public var postOnboardingFavoriteCount: Int { state.postOnboardingFavoriteCount }

    public func recordDeferral() {
        update { state in
            state.deferralCount += 1
            state.lastDeferredAt = self.now()
        }
    }

    @discardableResult
    public func recordPostOnboardingFavorite() -> Int {
        update { state in
            state.postOnboardingFavoriteCount += 1
        }
        return state.postOnboardingFavoriteCount
    }

    public func hasReachedDeferralCap(_ cap: Int) -> Bool {
        state.deferralCount >= cap
    }

    public func reset() {
        state = .default
        appStateStorage.removeValue(forKey: StorageKey.state)
    }

    private func update(_ mutate: (inout PushPermissionState) -> Void) {
        var next = state
        mutate(&next)
        state = next
        appStateStorage.setValue(next, forKey: StorageKey.state)
    }

    private enum StorageKey {
        static let state = "laughtrack.notifications.softPushPermissionState"
    }
}
