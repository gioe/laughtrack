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
        #expect(rootPadding - detailPadding == PodcastMiniPlayerLayout.rootTabBarClearance)
        #expect(PodcastMiniPlayerLayout.rootTabBarClearance < RootScrollBottomSpacing.floatingTabBarClearance)
    }
}
