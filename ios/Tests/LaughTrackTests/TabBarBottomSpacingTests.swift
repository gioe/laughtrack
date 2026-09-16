import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackApp

@Suite("Tab bar bottom spacing")
struct TabBarBottomSpacingTests {
    @Test("root scroll bottom padding clears the floating tab bar")
    func rootScrollBottomPaddingClearsFloatingTabBar() {
        let theme = LaughTrackTheme()

        #expect(RootScrollBottomSpacing.padding(theme: theme) >= 88)
        #expect(RootScrollBottomSpacing.padding(theme: theme) > theme.laughTrackTokens.browseDensity.heroPadding)
    }

    @Test("podcast mini player adds extra root scroll clearance")
    func podcastMiniPlayerAddsExtraRootScrollClearance() {
        let theme = LaughTrackTheme()
        let base = RootScrollBottomSpacing.padding(theme: theme, isPodcastMiniPlayerVisible: false)
        let withMiniPlayer = RootScrollBottomSpacing.padding(theme: theme, isPodcastMiniPlayerVisible: true)

        #expect(withMiniPlayer > base)
        #expect(withMiniPlayer - base >= RootScrollBottomSpacing.podcastMiniPlayerClearance)
    }

    @Test("root shell mini player clears the floating tab bar")
    func rootShellMiniPlayerClearsFloatingTabBar() {
        let theme = LaughTrackTheme()
        let rootPadding = PodcastMiniPlayerLayout.bottomPadding(theme: theme, clearsRootTabBar: true)
        let detailPadding = PodcastMiniPlayerLayout.bottomPadding(theme: theme, clearsRootTabBar: false)

        #expect(rootPadding > detailPadding)
        #expect(matchesRootTabBarClearance(rootPadding - detailPadding))
        #expect(PodcastMiniPlayerLayout.rootTabBarClearance < RootScrollBottomSpacing.floatingTabBarClearance)
    }

    @Test("root tab bar clearance accepts representable rounding", arguments: [
        PodcastMiniPlayerLayout.rootTabBarClearance.nextDown,
        PodcastMiniPlayerLayout.rootTabBarClearance,
        PodcastMiniPlayerLayout.rootTabBarClearance.nextUp,
    ])
    func rootTabBarClearanceAcceptsRepresentableRounding(actualClearance: CGFloat) {
        #expect(matchesRootTabBarClearance(actualClearance))
    }

    @Test("root tab bar clearance rejects meaningful layout drift", arguments: [
        CGFloat(-1), CGFloat(-0.25), CGFloat(0.25), CGFloat(1),
    ])
    func rootTabBarClearanceRejectsMeaningfulLayoutDrift(drift: CGFloat) {
        #expect(!matchesRootTabBarClearance(PodcastMiniPlayerLayout.rootTabBarClearance + drift))
    }

    private func matchesRootTabBarClearance(_ actualClearance: CGFloat) -> Bool {
        // Subtracting layout paddings can round by a few ULPs. This tolerance
        // is far below a screen pixel and still rejects meaningful layout drift.
        abs(actualClearance - PodcastMiniPlayerLayout.rootTabBarClearance) < 0.000001
    }
}
