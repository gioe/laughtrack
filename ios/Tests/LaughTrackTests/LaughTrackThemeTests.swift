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
}
