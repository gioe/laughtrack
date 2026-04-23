import Testing
import LaughTrackBridge

@Suite("LaughTrackTheme")
struct LaughTrackThemeTests {

    @Test("semantic LaughTrack tokens are exposed through the bridge")
    func semanticTokensAreAvailable() {
        let theme = LaughTrackTheme()

        #expect(theme.laughTrack.spacing.heroPadding > theme.spacing.xl)
        #expect(theme.laughTrack.radius.heroPanel > theme.cornerRadius.lg)
        #expect(theme.laughTrackTokens.spacing.heroPadding == theme.laughTrack.spacing.heroPadding)
    }

    @Test("generic app theme groups stay aligned with semantic LaughTrack roles")
    func genericThemeMapsToSemanticRoles() {
        let theme = LaughTrackTheme()

        #expect(theme.spacing.section == theme.laughTrack.spacing.sectionGap)
        #expect(theme.cornerRadius.full == theme.laughTrack.radius.pill)
        #expect(theme.typography.button == theme.laughTrack.typography.action)
        #expect(theme.iconSizes.huge >= theme.iconSizes.lg)
    }

    @Test("browse tokens expose denser defaults without collapsing surfaces")
    func browseTokensExposeDenseSurfaceDefaults() {
        let theme = LaughTrackTheme()

        #expect(theme.laughTrack.browseDensity.compactCardPadding < theme.laughTrack.spacing.cardPadding)
        #expect(theme.laughTrack.browseDensity.resultRowMinHeight < 96)
        #expect(theme.laughTrack.colors.canvas != theme.laughTrack.colors.surfaceElevated)
        #expect(theme.laughTrackTokens.browseDensity.heroPadding == theme.laughTrack.browseDensity.heroPadding)
    }
}
