import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct ProfileView: View {
    let apiClient: Client
    let signedOutMessage: String?
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    @Environment(\.appTheme) private var theme

    init(
        apiClient: Client,
        signedOutMessage: String?,
        nearbyPreferenceStore: NearbyPreferenceStore
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self._nearbyPreferenceStore = ObservedObject(wrappedValue: nearbyPreferenceStore)
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
                    nearbyPreferenceStore: nearbyPreferenceStore
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
