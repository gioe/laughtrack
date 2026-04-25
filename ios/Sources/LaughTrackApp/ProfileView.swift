import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct ProfileView: View {
    static let signedOutHeroTitle = "Sign in to LaughTrack"

    static func heroTitle(for provider: AuthProvider?) -> String {
        let providerName = provider?.displayName ?? "Saved session"
        return "Your \(providerName) account"
    }

    let apiClient: Client
    let signedOutMessage: String?

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme

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
                if let session = authManager.currentSession {
                    authenticatedHero(session: session)
                    accountCard(session: session)
                } else {
                    signedOutHero
                    if let signedOutMessage {
                        LaughTrackAuthMessageCard(message: signedOutMessage)
                    }
                    signInProvidersSection
                }
                settingsLinkSection
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.vertical, tokens.browseDensity.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.profileTabScreen)
        .background(tokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Profile")
        .modifier(LaughTrackNavigationChrome(background: tokens.colors.canvas))
    }

    @ViewBuilder
    private func authenticatedHero(session: AuthSessionMetadata) -> some View {
        LaughTrackHeroModule(
            eyebrow: "Profile",
            title: Self.heroTitle(for: session.provider),
            subtitle: "Account-level controls live here. Browse defaults moved to Settings."
        )
    }

    private var signedOutHero: some View {
        LaughTrackHeroModule(
            eyebrow: "Profile",
            title: Self.signedOutHeroTitle,
            subtitle: "Save favorites across devices and recover cleanly when sign-in is interrupted."
        )
    }

    @ViewBuilder
    private func accountCard(session: AuthSessionMetadata) -> some View {
        let laughTrack = theme.laughTrackTokens

        LaughTrackCard {
            VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                HStack(alignment: .top, spacing: laughTrack.spacing.itemGap) {
                    LaughTrackAvatar(
                        style: .symbol(session.provider?.symbolName ?? "person.crop.circle")
                    )

                    VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                        Text(session.provider?.displayName ?? "Saved session")
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)

                        Text(
                            session.expiresAt.map {
                                "Session expires \($0.formatted(.dateTime.month().day().hour().minute()))."
                            } ?? "Session expiration is not available."
                        )
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                    }
                }

                LaughTrackButton(
                    "Sign out",
                    systemImage: "rectangle.portrait.and.arrow.right",
                    tone: .destructive
                ) {
                    Task {
                        await authManager.signOut()
                    }
                }
            }
        }
    }

    private var settingsLinkSection: some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Settings",
                title: "Browse defaults",
                subtitle: "Saved nearby ZIP, distance, and notification preferences live in Settings."
            )
            LaughTrackButton(
                "Open Settings",
                systemImage: "gearshape",
                tone: .tertiary
            ) {
                coordinator.push(.settings)
            }
        }
    }

    private var signInProvidersSection: some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Sign in",
                title: "Save favorites across sessions",
                subtitle: "Sign in when you want synced favorite comedians and recovery messaging tied to a real account."
            )

            VStack(spacing: laughTrack.spacing.itemGap) {
                ForEach(AuthProvider.allCases, id: \.self) { provider in
                    LaughTrackAuthProviderCard(provider: provider) {
                        Task {
                            await authManager.signIn(with: provider)
                        }
                    }
                }
            }
        }
    }
}
