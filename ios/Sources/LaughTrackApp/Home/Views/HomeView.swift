import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct HomeView: View {
    let apiClient: Client
    let signedOutMessage: String?
    let searchNavigationBridge: SearchNavigationBridge

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: laughTrack.browseDensity.shelfGap) {
                LaughTrackSectionHeader(
                    eyebrow: "Home",
                    title: "Comedy worth noticing nearby",
                    subtitle: "Browse local momentum, featured shows, and venue spotlights before dropping into Search."
                )

                SessionBannerCard(signedOutMessage: signedOutMessage)

                VStack(alignment: .leading, spacing: theme.spacing.md) {
                    LaughTrackHeroModule(
                        eyebrow: "Search",
                        title: "Jump back into Search",
                        subtitle: "Move between Shows, Clubs, and Comedians without leaving the same working surface.",
                        ctaTitle: "Shows, clubs, and comics"
                    )

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: theme.spacing.sm) {
                            LaughTrackBrowseChip("Near Me ready", systemImage: "location.fill", tone: .selected)
                            LaughTrackBrowseChip("Upcoming dates first", systemImage: "sparkles", tone: .accent)
                            LaughTrackBrowseChip("Favorites in profile", systemImage: "star.fill")
                        }
                        .padding(.horizontal, 1)
                    }
                }

                HomeSearchEntryRail(searchNavigationBridge: searchNavigationBridge)

                HomeNearbyDiscoverySection(
                    apiClient: apiClient,
                    nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
                    nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self)
                )

                DiscoveryHubView(
                    apiClient: apiClient,
                    nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self)
                )
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.vertical, laughTrack.browseDensity.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.homeScreen)
        .background(laughTrack.colors.canvas.ignoresSafeArea())
        .background(
            laughTrack.gradients.heroWash
                .frame(maxHeight: 280)
                .ignoresSafeArea(edges: .top),
            alignment: .top
        )
        .navigationTitle("LaughTrack")
        .toolbar {
            ToolbarItem(placement: toolbarPlacement) {
                Button {
                    coordinator.push(authManager.currentSession == nil ? .profile : .settings)
                } label: {
                    Image(systemName: authManager.currentSession == nil ? "person.crop.circle.badge.plus" : "gearshape")
                }
                .accessibilityLabel(authManager.currentSession == nil ? "Sign in" : "Settings")
                .accessibilityIdentifier(LaughTrackViewTestID.homeSettingsButton)
            }
        }
        .modifier(LaughTrackNavigationChrome(background: laughTrack.colors.canvas))
    }

    private var toolbarPlacement: ToolbarItemPlacement {
        #if os(iOS)
        .topBarTrailing
        #else
        .primaryAction
        #endif
    }
}

private struct HomeSearchEntryRail: View {
    let searchNavigationBridge: SearchNavigationBridge

    @Environment(\.appTheme) private var theme

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.md) {
            LaughTrackShelfHeader(
                eyebrow: "Search entry points",
                title: "Open Search from a head start",
                subtitle: "Pick what you’re browsing first, then refine in place."
            )

            VStack(spacing: theme.spacing.sm) {
                HomeSearchEntryCard(config: .shows, searchNavigationBridge: searchNavigationBridge)
                HomeSearchEntryCard(config: .clubs, searchNavigationBridge: searchNavigationBridge)
                HomeSearchEntryCard(config: .comedians, searchNavigationBridge: searchNavigationBridge)
            }
        }
    }
}
