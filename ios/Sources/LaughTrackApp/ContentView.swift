import SwiftUI
import LaughTrackBridge
import LaughTrackCore
import LaughTrackAPIClient

struct ContentView: View {
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme
    @StateObject private var favorites = ComedianFavoriteStore()
    @StateObject private var nearbyPreferenceStore = NearbyPreferenceStore()

    var body: some View {
        Group {
            switch authManager.state {
            case .restoring:
                AuthLoadingView(message: "Restoring your LaughTrack session…")
            case .signingIn(let provider):
                AuthLoadingView(message: "Finishing \(provider.displayName) sign-in…")
            case .signedOut(let message):
                appShell(signedOutMessage: message)
            case .authenticated:
                appShell(signedOutMessage: nil)
            }
        }
        .environmentObject(favorites)
        .tint(theme.colors.primary)
        .task {
            await authManager.restoreSessionIfNeeded()
        }
    }

    @ViewBuilder
    private func appShell(signedOutMessage: String?) -> some View {
        CoordinatedNavigationStack(coordinator: coordinator) { route in
            switch route {
            case .home:
                HomeView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    nearbyPreferenceStore: nearbyPreferenceStore
                )
            case .settings:
                SettingsView(
                    signedOutMessage: signedOutMessage,
                    nearbyPreferenceStore: nearbyPreferenceStore
                )
            case .showDetail(let id):
                ShowDetailView(showID: id, apiClient: apiClient)
            case .comedianDetail(let id):
                ComedianDetailView(comedianID: id, apiClient: apiClient)
            case .clubDetail(let id):
                ClubDetailView(clubID: id, apiClient: apiClient)
            }
        } root: {
            HomeView(
                apiClient: apiClient,
                signedOutMessage: signedOutMessage,
                nearbyPreferenceStore: nearbyPreferenceStore
            )
        }
    }
}

struct HomeView: View {
    let apiClient: Client
    let signedOutMessage: String?
    let nearbyPreferenceStore: NearbyPreferenceStore

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: theme.spacing.xl) {
                LaughTrackSectionHeader(
                    eyebrow: "Discovery",
                    title: "Find comedy shows nearby",
                    subtitle: "Browse live show results first, then refine by comedian, club, location, date, and sort without leaving the home screen."
                )

                SessionBannerCard(signedOutMessage: signedOutMessage)

                HomeNearbyDiscoverySection(
                    apiClient: apiClient,
                    nearbyPreferenceStore: nearbyPreferenceStore
                )

                DiscoveryHubView(
                    apiClient: apiClient,
                    nearbyPreferenceStore: nearbyPreferenceStore
                )
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.vertical, laughTrack.spacing.heroPadding)
        }
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
                    coordinator.push(.settings)
                } label: {
                    Image(systemName: authManager.currentSession == nil ? "person.crop.circle.badge.plus" : "gearshape")
                }
                .accessibilityLabel("Settings")
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

struct SettingsView: View {
    let signedOutMessage: String?
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore

    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: laughTrack.spacing.sectionGap) {
                LaughTrackSectionHeader(
                    eyebrow: "Settings",
                    title: "Keep discovery grounded in real app state",
                    subtitle: "This screen only surfaces settings LaughTrack actually persists today, plus your current account state."
                )

                if let signedOutMessage {
                    LaughTrackCard {
                        Text(signedOutMessage)
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.accentStrong)
                    }
                }

                LaughTrackSectionHeader(
                    eyebrow: "Discovery",
                    title: "Nearby discovery",
                    subtitle: "Home and Settings share the same saved ZIP and search radius."
                )

                LaughTrackCard {
                    VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                        if let preference = nearbyPreferenceStore.preference {
                            Text("Saved nearby preference")
                                .font(laughTrack.typography.cardTitle)
                                .foregroundStyle(laughTrack.colors.textPrimary)

                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: theme.spacing.sm) {
                                    LaughTrackBadge(
                                        "ZIP \(preference.zipCode)",
                                        systemImage: "mappin.and.ellipse",
                                        tone: .neutral
                                    )
                                    LaughTrackBadge(
                                        "\(preference.distanceMiles) mi",
                                        systemImage: "location.fill",
                                        tone: .highlight
                                    )
                                    LaughTrackBadge(
                                        preference.source == .manual ? "Saved manually" : "Current location",
                                        systemImage: preference.source == .manual ? "slider.horizontal.3" : "location.north.line",
                                        tone: .accent
                                    )
                                }
                            }

                            Text("Adjust the search radius here or return home when you want to replace the ZIP itself.")
                                .font(laughTrack.typography.body)
                                .foregroundStyle(laughTrack.colors.textSecondary)

                            HStack(spacing: theme.spacing.sm) {
                                LaughTrackButton("Radius -5", systemImage: "minus", tone: .secondary, fullWidth: false) {
                                    updateNearbyRadius(by: -5)
                                }
                                .disabled(preference.distanceMiles <= 5)

                                LaughTrackButton("Radius +5", systemImage: "plus", tone: .secondary, fullWidth: false) {
                                    updateNearbyRadius(by: 5)
                                }
                            }

                            LaughTrackButton(
                                "Clear saved nearby preference",
                                systemImage: "location.slash",
                                tone: .tertiary
                            ) {
                                nearbyPreferenceStore.clear()
                            }
                        } else {
                            Text("No nearby ZIP is saved yet.")
                                .font(laughTrack.typography.cardTitle)
                                .foregroundStyle(laughTrack.colors.textPrimary)
                            Text("Set a ZIP or use current location from Home when you want nearby shows to stay pinned across launches.")
                                .font(laughTrack.typography.body)
                                .foregroundStyle(laughTrack.colors.textSecondary)
                        }
                    }
                }

                if let session = authManager.currentSession {
                    LaughTrackSectionHeader(
                        eyebrow: "Account",
                        title: "Session details",
                        subtitle: "Authentication state shares the same reusable card shell as the rest of the app."
                    )

                    LaughTrackCard {
                        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
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
                } else {
                    LaughTrackSectionHeader(
                        eyebrow: "Sign in",
                        title: "Bring favorites and alerts with you",
                        subtitle: "Use the same LaughTrack auth surfaces for Apple, Google, and recovery states without changing the token-backed flow underneath."
                    )

                    LaughTrackCard(tone: .accent) {
                        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                            Text("LaughTrack account")
                                .font(laughTrack.typography.eyebrow)
                                .foregroundStyle(laughTrack.colors.textInverse.opacity(0.78))
                                .textCase(.uppercase)
                            Text("Sign in once, then keep your comedy world in sync.")
                                .font(laughTrack.typography.screenTitle)
                                .foregroundStyle(laughTrack.colors.textInverse)
                            Text("Saved comedians, favorite actions, and recovery messaging all stay in the same native component system instead of dropping into a temporary shell.")
                                .font(laughTrack.typography.body)
                                .foregroundStyle(laughTrack.colors.textInverse.opacity(0.92))
                        }
                    }

                    if let signedOutMessage {
                        LaughTrackAuthMessageCard(message: signedOutMessage)
                    }

                    VStack(spacing: laughTrack.spacing.itemGap) {
                        ForEach(AuthProvider.allCases, id: \.self) { provider in
                            LaughTrackAuthProviderCard(provider: provider) {
                                Task {
                                    await authManager.signIn(with: provider)
                                }
                            }
                        }
                    }

                    LaughTrackCard(tone: .muted) {
                        VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                            Text("What you unlock")
                                .font(laughTrack.typography.metadata)
                                .foregroundStyle(laughTrack.colors.accent)
                                .textCase(.uppercase)
                            Text("Save comedians faster, recover cleanly if a browser handoff fails, and keep the auth copy consistent with discovery and detail screens.")
                                .font(laughTrack.typography.body)
                                .foregroundStyle(laughTrack.colors.textSecondary)
                        }
                    }
                }
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.vertical, laughTrack.spacing.heroPadding)
        }
        .background(laughTrack.colors.canvas.ignoresSafeArea())
        .navigationTitle("Settings")
    }

    private func updateNearbyRadius(by delta: Int) {
        guard let preference = nearbyPreferenceStore.preference else { return }
        nearbyPreferenceStore.setDistance(max(5, preference.distanceMiles + delta))
    }
}

private struct SessionBannerCard: View {
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    let signedOutMessage: String?

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        LaughTrackCard {
            VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                Text(authManager.currentSession == nil ? "Browsing as guest" : "Signed in")
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .textCase(.uppercase)

                if let session = authManager.currentSession {
                    Text(session.provider?.displayName ?? "Saved mobile session")
                        .font(laughTrack.typography.cardTitle)
                        .foregroundStyle(laughTrack.colors.textPrimary)
                    Text(
                        session.expiresAt.map {
                            "Favorite actions are enabled. Your session expires \($0.formatted(.dateTime.month().day().hour().minute()))."
                        } ?? "Favorite actions are enabled for this session."
                    )
                    .font(laughTrack.typography.body)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                } else {
                    Text("Discovery stays open even when you’re signed out.")
                        .font(laughTrack.typography.cardTitle)
                        .foregroundStyle(laughTrack.colors.textPrimary)
                    Text(signedOutMessage ?? "Open Settings when you want to connect Apple or Google, sync favorites, and recover quickly if sign-in is interrupted.")
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                }
            }
        }
    }
}

private struct AuthLoadingView: View {
    @Environment(\.appTheme) private var theme

    let message: String

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(spacing: laughTrack.spacing.sectionGap) {
            LaughTrackCard(tone: .accent) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    Text("LaughTrack account")
                        .font(laughTrack.typography.eyebrow)
                        .foregroundStyle(laughTrack.colors.textInverse.opacity(0.78))
                        .textCase(.uppercase)
                    Text("Signing you in with the shared token flow.")
                        .font(laughTrack.typography.screenTitle)
                        .foregroundStyle(laughTrack.colors.textInverse)
                    Text("The browser handoff and session exchange stay the same; this screen now uses the same branded cards and typography as the rest of the app.")
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textInverse.opacity(0.92))
                }
            }

            LaughTrackStateView(
                tone: .loading,
                title: "Loading LaughTrack",
                message: message
            )
        }
        .padding(theme.spacing.xl)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
    }
}

private struct LaughTrackNavigationChrome: ViewModifier {
    let background: Color

    func body(content: Content) -> some View {
        #if os(iOS)
        content
            .toolbarBackground(background, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
        #else
        content
        #endif
    }
}
