import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

/// Notification recall surface reached from the profile-button menu. Renders
/// the comedian-arrival history returned by GET /me/notifications (capped at
/// the 100 most-recent — a bounded list, not infinite scroll) and deep-links a
/// tapped row to the show. Opening the screen marks everything seen so the
/// profile-button unread badge clears.
struct NotificationCenterView: View {
    let apiClient: Client

    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme

    @StateObject private var model = NotificationCenterModel()

    var body: some View {
        let tokens = theme.laughTrackTokens

        Group {
            switch model.phase {
            case .idle, .loading:
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .failure(let message):
                NotificationCenterPlaceholder(
                    systemImage: "bell.slash",
                    title: "Notifications unavailable",
                    message: message,
                    retry: { await model.reload(apiClient: apiClient) }
                )
            case .loaded(let items) where items.isEmpty:
                NotificationCenterPlaceholder(
                    systemImage: "bell",
                    title: "No notifications yet",
                    message: "When a comedian you follow has a show near you, you'll see it here.",
                    retry: nil
                )
            case .loaded(let items):
                ScrollView {
                    LazyVStack(spacing: theme.spacing.sm) {
                        ForEach(items) { item in
                            Button {
                                coordinator.push(.showDetail(item.showId))
                            } label: {
                                NotificationRow(item: item)
                            }
                            .buttonStyle(.plain)
                            .accessibilityIdentifier(LaughTrackViewTestID.notificationRow)
                        }
                    }
                    .padding(theme.spacing.lg)
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(tokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Notifications")
        .modifier(LaughTrackNavigationChrome(background: tokens.colors.canvas))
        .accessibilityIdentifier(LaughTrackViewTestID.notificationCenterScreen)
        .task {
            await model.loadIfNeeded(apiClient: apiClient)
            // Opening the center is the "seen" signal. Stamp the high-water
            // mark, then refresh currentUser so the profile-button badge
            // (driven by /me notificationsUnreadCount) clears on next render.
            if await model.markSeen(apiClient: apiClient) {
                await authManager.refreshCurrentUser()
            }
        }
    }
}

private struct NotificationRow: View {
    let item: NotificationCenterItem

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        HStack(alignment: .top, spacing: theme.spacing.sm) {
            // Unread dot keeps the read/unread distinction visible for the
            // current session even though opening the center clears the badge.
            Circle()
                .fill(item.isUnread ? tokens.colors.accentStrong : Color.clear)
                .frame(width: 8, height: 8)
                .padding(.top, 6)

            VStack(alignment: .leading, spacing: theme.spacing.xs) {
                Text(item.title)
                    .font(laughTrackBody.weight(.semibold))
                    .foregroundStyle(tokens.colors.textPrimary)
                if !item.body.isEmpty {
                    Text(item.body)
                        .font(laughTrackMetadata)
                        .foregroundStyle(tokens.colors.textSecondary)
                }
                HStack(spacing: theme.spacing.xs) {
                    ForEach(item.channels, id: \.self) { channel in
                        Text(channel.uppercased())
                            .font(laughTrackMetadata)
                            .foregroundStyle(tokens.colors.accent)
                            .padding(.horizontal, theme.spacing.xs)
                            .padding(.vertical, 2)
                            .overlay(
                                Capsule(style: .continuous)
                                    .stroke(tokens.colors.borderSubtle, lineWidth: 1)
                            )
                    }
                    if let relative = relativeSentAt {
                        Text(relative)
                            .font(laughTrackMetadata)
                            .foregroundStyle(tokens.colors.textSecondary)
                    }
                }
            }

            Spacer(minLength: 0)

            Image(systemName: "chevron.right")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(tokens.colors.textSecondary)
                .padding(.top, 4)
        }
        .padding(theme.spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(tokens.colors.surfaceElevated)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(tokens.colors.borderSubtle, lineWidth: 1)
        )
        .accessibilityElement(children: .combine)
    }

    private var laughTrackBody: Font { theme.laughTrackTokens.typography.body }
    private var laughTrackMetadata: Font { theme.laughTrackTokens.typography.metadata }

    private var relativeSentAt: String? {
        guard let sentAt = item.sentAt else { return nil }
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: sentAt, relativeTo: Date())
    }
}

private struct NotificationCenterPlaceholder: View {
    let systemImage: String
    let title: String
    let message: String
    let retry: (() async -> Void)?

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        VStack(spacing: theme.spacing.md) {
            Image(systemName: systemImage)
                .font(.system(size: 44, weight: .regular))
                .foregroundStyle(tokens.colors.textSecondary)
            Text(title)
                .font(tokens.typography.body.weight(.semibold))
                .foregroundStyle(tokens.colors.textPrimary)
            Text(message)
                .font(tokens.typography.metadata)
                .foregroundStyle(tokens.colors.textSecondary)
                .multilineTextAlignment(.center)
            if let retry {
                Button("Try again") {
                    Task { await retry() }
                }
                .font(tokens.typography.body.weight(.semibold))
                .foregroundStyle(tokens.colors.accent)
            }
        }
        .padding(theme.spacing.xl)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
