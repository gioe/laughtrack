import SwiftUI
import LaughTrackBridge
import LaughTrackCore

struct ContentView: View {
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    var body: some View {
        Group {
            switch authManager.state {
            case .restoring:
                AuthLoadingView(message: "Restoring your LaughTrack session…")
            case .signingIn(let provider):
                AuthLoadingView(message: "Finishing \(provider.displayName) sign-in…")
            case .signedOut(let message):
                AuthenticationGateView(message: message)
            case .authenticated:
                CoordinatedNavigationStack(coordinator: coordinator) { route in
                    switch route {
                    case .home:
                        HomeView()
                    case .settings:
                        SettingsView()
                    }
                } root: {
                    HomeView()
                }
            }
        }
        .tint(theme.colors.primary)
        .task {
            await authManager.restoreSessionIfNeeded()
        }
    }
}

struct HomeView: View {
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: theme.spacing.xxl) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    Text("Live comedy, tuned for the LaughTrack brand.")
                        .font(laughTrack.typography.eyebrow)
                        .foregroundStyle(laughTrack.colors.accentMuted)
                        .textCase(.uppercase)
                    Text("Welcome to LaughTrack")
                        .font(laughTrack.typography.hero)
                        .foregroundStyle(laughTrack.colors.textInverse)
                    Text("The app now reads a dedicated native theme layer for colors, typography, spacing, corners, shadows, and motion.")
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textInverse.opacity(0.92))
                }

                SessionStatusCard()

                VStack(alignment: .leading, spacing: laughTrack.spacing.clusterGap) {
                    VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                        Text("Tonight's vibe")
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .textCase(.uppercase)
                        Text("Warm canvas, cedar headlines, copper accents.")
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                        Text("These names mirror the web brand system semantically, so app code can ask for roles like canvas, accent, hero, and card instead of raw one-off styling.")
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                    }

                    Button {
                        withAnimation(laughTrack.motion.tapFeedback) {
                            coordinator.push(.settings)
                        }
                    } label: {
                        HStack(spacing: laughTrack.spacing.itemGap) {
                            Image(systemName: "slider.horizontal.3")
                                .font(.system(size: theme.iconSizes.md, weight: .semibold))
                            Text("Open theme settings")
                                .font(laughTrack.typography.action)
                        }
                        .foregroundStyle(laughTrack.colors.textInverse)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, theme.spacing.lg)
                        .background(laughTrack.colors.accent)
                        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous))
                        .shadowStyle(laughTrack.shadows.floating)
                    }
                    .buttonStyle(.plain)
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
        .modifier(LaughTrackNavigationChrome(background: laughTrack.colors.canvas))
    }
}

struct SettingsView: View {
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        List {
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

            Section("Account") {
                if let session = authManager.currentSession {
                    LabeledContent("Signed in with") {
                        Text(session.provider?.displayName ?? "Saved session")
                    }
                    if let expiresAt = session.expiresAt {
                        LabeledContent("Session expires") {
                            Text(expiresAt.formatted(.dateTime.month().day().hour().minute()))
                        }
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
        }
        .scrollContentBackground(.hidden)
        .background(laughTrack.colors.canvas)
        .navigationTitle("Settings")
    }
}

private struct AuthenticationGateView: View {
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    let message: String?

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: laughTrack.spacing.clusterGap) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    Text("Native sign-in")
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.accentMuted)
                        .textCase(.uppercase)
                    Text("Pick up where the web session leaves off.")
                        .font(laughTrack.typography.hero)
                        .foregroundStyle(laughTrack.colors.textInverse)
                    Text("Apple and Google both run through LaughTrack’s existing web auth, then the app boots a mobile JWT session and stores it securely for relaunch.")
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textInverse.opacity(0.92))
                }

                if let message {
                    Text(message)
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.accent)
                        .padding(theme.spacing.lg)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(laughTrack.colors.surfaceElevated)
                        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
                }

                VStack(spacing: theme.spacing.md) {
                    ForEach(AuthProvider.allCases, id: \.self) { provider in
                        AuthProviderButton(provider: provider)
                    }
                }
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
            .shadowStyle(laughTrack.shadows.card)
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

private struct SessionStatusCard: View {
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    var body: some View {
        guard let session = authManager.currentSession else {
            return AnyView(EmptyView())
        }

        let laughTrack = theme.laughTrackTokens

        return AnyView(
            VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                Text("Signed in")
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .textCase(.uppercase)
                Text(session.provider?.displayName ?? "Saved mobile session")
                    .font(laughTrack.typography.cardTitle)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                Text(
                    session.expiresAt.map {
                        "JWT session restored from secure storage. It expires \($0.formatted(.dateTime.month().day().hour().minute()))."
                    } ?? "JWT session restored from secure storage."
                )
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textSecondary)
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
        )
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
