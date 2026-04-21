import SwiftUI
import LaughTrackBridge

struct ContentView: View {
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme

    var body: some View {
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
        .tint(theme.colors.primary)
    }
}

struct HomeView: View {
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
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
        }
        .scrollContentBackground(.hidden)
        .background(laughTrack.colors.canvas)
        .navigationTitle("Settings")
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
