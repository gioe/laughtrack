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
                HomeView(apiClient: apiClient, signedOutMessage: signedOutMessage)
            case .settings:
                SettingsView(signedOutMessage: signedOutMessage)
            case .showDetail(let id):
                ShowDetailView(showID: id, apiClient: apiClient)
            case .comedianDetail(let id):
                ComedianDetailView(comedianID: id, apiClient: apiClient)
            case .clubDetail(let id):
                ClubDetailView(clubID: id, apiClient: apiClient)
            }
        } root: {
            HomeView(apiClient: apiClient, signedOutMessage: signedOutMessage)
        }
    }
}

struct HomeView: View {
    let apiClient: Client
    let signedOutMessage: String?

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: theme.spacing.xl) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    Text("Discover")
                        .font(laughTrack.typography.eyebrow)
                        .foregroundStyle(laughTrack.colors.accentMuted)
                        .textCase(.uppercase)
                    Text("Shows, comedians, and clubs")
                        .font(laughTrack.typography.hero)
                        .foregroundStyle(laughTrack.colors.textInverse)
                    Text("Browse the live API in native detail screens, then save favorite comedians wherever they appear.")
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textInverse.opacity(0.92))
                }

                SessionBannerCard(signedOutMessage: signedOutMessage)

                DiscoveryHubView(apiClient: apiClient)
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
                .accessibilityLabel("Open settings")
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

    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        List {
            if let signedOutMessage {
                Section {
                    Text(signedOutMessage)
                        .foregroundStyle(laughTrack.colors.accent)
                }
            }

            Section("Theme") {
                HStack {
                    Text("Canvas")
                    Spacer()
                    Circle()
                        .fill(laughTrack.colors.canvas)
                        .frame(width: 18, height: 18)
                }
                HStack {
                    Text("Accent")
                    Spacer()
                    Circle()
                        .fill(laughTrack.colors.accent)
                        .frame(width: 18, height: 18)
                }
                HStack {
                    Text("Motion")
                    Spacer()
                    Text("Spring")
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                }
            }

            if let session = authManager.currentSession {
                Section("Account") {
                    LabeledContent("Signed in with") {
                        Text(session.provider?.displayName ?? "Saved session")
                    }
                    if let expiresAt = session.expiresAt {
                        LabeledContent("Session expires") {
                            Text(expiresAt.formatted(.dateTime.month().day().hour().minute()))
                        }
                    }

                    Button(role: .destructive) {
                        Task {
                            await authManager.signOut()
                        }
                    } label: {
                        Text("Sign out")
                    }
                }
            } else {
                Section("Sign in") {
                    ForEach(AuthProvider.allCases, id: \.self) { provider in
                        AuthProviderButton(provider: provider)
                            .listRowBackground(laughTrack.colors.canvas)
                    }
                }
            }
        }
        .scrollContentBackground(.hidden)
        .background(laughTrack.colors.canvas)
        .navigationTitle("Settings")
    }
}

private struct SessionBannerCard: View {
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    let signedOutMessage: String?

    var body: some View {
        let laughTrack = theme.laughTrackTokens

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
                Text(signedOutMessage ?? "Open Settings when you want to connect Apple or Google and save comedians.")
                    .font(laughTrack.typography.body)
                    .foregroundStyle(laughTrack.colors.textSecondary)
            }
        }
        .padding(theme.spacing.xl)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(laughTrack.colors.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .shadowStyle(laughTrack.shadows.card)
    }
}

private struct AuthProviderButton: View {
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    let provider: AuthProvider

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button {
            Task {
                await authManager.signIn(with: provider)
            }
        } label: {
            HStack(spacing: theme.spacing.md) {
                Image(systemName: provider.symbolName)
                    .font(.system(size: theme.iconSizes.md, weight: .semibold))
                VStack(alignment: .leading, spacing: 4) {
                    Text(provider.title)
                        .font(laughTrack.typography.action)
                    Text(provider.subtitle)
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                }
                Spacer()
                Image(systemName: "arrow.up.right")
                    .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.textSecondary)
            }
            .foregroundStyle(laughTrack.colors.textPrimary)
            .padding(theme.spacing.lg)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(laughTrack.colors.surfaceElevated)
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                    .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }
}

private struct AuthLoadingView: View {
    @Environment(\.appTheme) private var theme

    let message: String

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(spacing: theme.spacing.lg) {
            ProgressView()
                .progressViewStyle(.circular)
                .tint(laughTrack.colors.accent)
            Text(message)
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textPrimary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(laughTrack.colors.canvas.ignoresSafeArea())
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
