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
    @Environment(\.serviceContainer) private var serviceContainer

    @StateObject private var model = NotificationCenterModel()
    @State private var openDropdownID: String?

    private var analytics: (any AnalyticsManagerProtocol)? {
        serviceContainer.resolveOptional(AnalyticsManagerProtocol.self)
    }

    var body: some View {
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
            case .loaded:
                ScrollView {
                    LazyVStack(spacing: theme.spacing.sm) {
                        NotificationSortPicker(
                            selection: $model.sort,
                            openDropdownID: $openDropdownID
                        )

                        ForEach(model.sortedItems) { item in
                            Button {
                                switch item.tap {
                                case .show(let showId):
                                    analytics?.track(
                                        NotificationsAnalyticsEvents.cardTapped,
                                        parameters: [
                                            NotificationsAnalyticsEvents.Param.showId: showId
                                        ]
                                    )
                                    coordinator.push(.showDetail(showId))
                                case .favorites:
                                    analytics?.track(
                                        NotificationsAnalyticsEvents.cardTapped,
                                        parameters: [
                                            NotificationsAnalyticsEvents.Param.showId: 0
                                        ]
                                    )
                                    coordinator.push(.library)
                                }
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
        .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
        .navigationTitle("Notifications")
        .modifier(InlineNavigationTitle())
        .modifier(LaughTrackNavigationChrome(background: .clear))
        .accessibilityIdentifier(LaughTrackViewTestID.notificationCenterScreen)
        .overlayPreferenceValue(PillDropdownAnchorKey.self) { anchors in
            GeometryReader { proxy in
                PillDropdownOverlay(
                    id: NotificationSortPicker.dropdownID,
                    options: NotificationSortOption.allCases,
                    selected: $model.sort,
                    triggerLabel: { $0.title },
                    optionLabel: { $0.title },
                    openDropdownID: $openDropdownID,
                    anchors: anchors,
                    proxy: proxy
                )
            }
        }
        .task {
            await model.loadIfNeeded(apiClient: apiClient)
            // Opening the center is the "seen" signal — but only mark seen once
            // the feed actually loaded. Marking seen after a failed/never-loaded
            // fetch would stamp the high-water mark and silently clear
            // notifications the user never got to see. On success, refresh
            // currentUser so the profile-button badge (driven by /me
            // notificationsUnreadCount) clears on next render.
            guard case .loaded = model.phase else { return }
            // Record the open with the count that was waiting, before mark-seen
            // zeroes it.
            analytics?.track(
                NotificationsAnalyticsEvents.viewed,
                parameters: [
                    NotificationsAnalyticsEvents.Param.unreadCount: model.unreadCount
                ]
            )
            if await model.markSeen(apiClient: apiClient) {
                await authManager.refreshCurrentUser()
            }
        }
    }
}

private struct NotificationSortPicker: View {
    static let dropdownID = "notifications-sort"

    @Binding var selection: NotificationSortOption
    @Binding var openDropdownID: String?

    @Environment(\.appTheme) private var theme

    var body: some View {
        PillDropdownTrigger(
            id: Self.dropdownID,
            selected: selection,
            triggerLabel: { "Sort: \($0.title)" },
            accessibilityLabel: { "Sort notifications by \($0.title)" },
            openDropdownID: $openDropdownID
        )
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.bottom, theme.spacing.xs)
        .accessibilityIdentifier("laughtrack.notifications.sort-picker")
    }
}

private struct NotificationRow: View {
    let item: NotificationCenterItem

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        HStack(alignment: .top, spacing: theme.spacing.sm) {
            comedianAvatar

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
                    ForEach(item.metadataLabels(relativeSentAt: relativeSentAt), id: \.self) { label in
                        Text(label)
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

    private var comedianAvatar: some View {
        let tokens = theme.laughTrackTokens

        return ZStack {
            Circle()
                .fill(tokens.colors.surfaceMuted)

            if let url = item.comedianImageURL {
                CachedAsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    avatarFallback
                } error: { _ in
                    avatarFallback
                }
            } else {
                avatarFallback
            }
        }
        .frame(width: 50, height: 50)
        .clipShape(Circle())
        .overlay(Circle().stroke(tokens.colors.borderStrong.opacity(0.45), lineWidth: 1))
        .shadowStyle(tokens.shadows.card)
        .overlay(alignment: .topTrailing) {
            if item.isUnread {
                Circle()
                    .fill(tokens.colors.accentStrong)
                    .frame(width: 10, height: 10)
                    .overlay(Circle().stroke(tokens.colors.surfaceElevated, lineWidth: 2))
                    .offset(x: 1, y: -1)
            }
        }
        .accessibilityHidden(true)
    }

    private var avatarFallback: some View {
        let tokens = theme.laughTrackTokens

        return Image(systemName: "person.fill")
            .font(.system(size: 20, weight: .semibold))
            .foregroundStyle(tokens.colors.accentStrong)
    }

    // Shared formatter — reused across every row body eval rather than
    // allocated per render (matches the static ISO formatters in the model).
    private static let relativeFormatter: RelativeDateTimeFormatter = {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter
    }()

    private var relativeSentAt: String? {
        guard let sentAt = item.sentAt else { return nil }
        return Self.relativeFormatter.localizedString(for: sentAt, relativeTo: Date())
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
