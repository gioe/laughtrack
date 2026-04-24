import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct ProfileView: View {
    let apiClient: Client
    let signedOutMessage: String?
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer

    init(
        apiClient: Client,
        signedOutMessage: String?
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
    }

    var body: some View {
        let tokens = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
                LaughTrackHeroModule(
                    eyebrow: "Profile",
                    title: "Your comedy setup",
                    subtitle: "Favorites, nearby defaults, and account controls live here."
                )

                SettingsView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self)
                )
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.vertical, tokens.browseDensity.heroPadding)
        }
        .background(tokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Profile")
        .modifier(LaughTrackNavigationChrome(background: tokens.colors.canvas))
    }
}
