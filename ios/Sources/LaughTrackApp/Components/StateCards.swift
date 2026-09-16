import SwiftUI
import LaughTrackBridge
import LaughTrackCore

struct LoadingCard: View {
    let title: String

    init(title: String = "Loading") {
        self.title = title
    }

    var body: some View {
        LaughTrackInlineStateCard(
            tone: .loading,
            title: title,
            message: "LaughTrack is fetching the latest data for this view."
        )
    }
}

struct EmptyCard: View {
    let title: String
    let message: String
    let actionTitle: String?
    let action: (() -> Void)?

    init(
        title: String = "Nothing here yet",
        message: String,
        actionTitle: String? = nil,
        action: (() -> Void)? = nil
    ) {
        self.title = title
        self.message = message
        self.actionTitle = actionTitle
        self.action = action
    }

    var body: some View {
        LaughTrackInlineStateCard(
            tone: .empty,
            title: title,
            message: message,
            actionTitle: actionTitle,
            action: action
        )
    }
}

struct FailureCard: View {
    let failure: LoadFailure
    let retry: () async -> Void
    let signIn: () -> Void

    var body: some View {
        LaughTrackInlineStateCard(
            tone: .error,
            title: failure.defaultTitle,
            message: failure.message,
            actionTitle: actionTitle
        ) {
            performAction()
        }
    }

    private var actionTitle: String {
        switch failure.recoveryAction {
        case .signIn:
            return "Sign in"
        case .retry:
            return "Try again"
        }
    }

    private func performAction() {
        switch failure.recoveryAction {
        case .signIn:
            signIn()
        case .retry:
            Task { await retry() }
        }
    }
}

struct InlineStatusMessage: View {
    @Environment(\.appTheme) private var theme

    let message: String

    var body: some View {
        LaughTrackCard(tone: .muted, density: .compact) {
            HStack(alignment: .top, spacing: theme.spacing.sm) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(theme.laughTrackTokens.colors.accent)
                Text(message)
                    .font(theme.laughTrackTokens.typography.metadata)
                    .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

struct SearchResultsSummary: View {
    @Environment(\.appTheme) private var theme
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @ScaledMetric(relativeTo: .caption) private var statusHeight = 44

    let count: Int
    let total: Int
    let state: SearchResultsState
    let retry: () async -> Void
    let signIn: () -> Void

    var body: some View {
        HStack(spacing: theme.spacing.sm) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                if !state.isConfirmed {
                    Text(count == 0 ? "Previous search had no matches" : "Previous results shown")
                        .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                }
            }
            .font(theme.laughTrackTokens.typography.metadata)
            .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: theme.spacing.sm)
            if state == .updating {
                if reduceMotion {
                    Image(systemName: "hourglass")
                        .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                        .accessibilityHidden(true)
                } else {
                    ProgressView().controlSize(.small).accessibilityHidden(true)
                }
            } else if !state.isConfirmed {
                Button {
                    if case .failed(let failure) = state, failure.recoveryAction == .signIn {
                        signIn()
                    } else {
                        Task { await retry() }
                    }
                } label: {
                    Text(actionTitle)
                        .font(theme.laughTrackTokens.typography.metadata.weight(.semibold))
                        .frame(minWidth: 44, minHeight: 44)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .foregroundStyle(theme.laughTrackTokens.colors.accent)
                .accessibilityIdentifier("search-refresh-retry")
            }
        }
        // Reserve the same status space when settled; starting a refresh must
        // not insert a banner that pushes the existing rows down.
        .frame(minHeight: statusHeight)
        .accessibilityElement(children: .contain)
    }

    private var title: String {
        switch state {
        case .confirmed: return "Showing \(count.formatted(.number)) of \(total.formatted(.number))"
        case .updating: return "Updating results…"
        case .failed: return "Couldn’t update results"
        case .interrupted: return "Search paused"
        }
    }

    private var actionTitle: String {
        if case .failed(let failure) = state, failure.recoveryAction == .signIn { return "Sign in" }
        return "Retry"
    }
}

/// Only the result surface dims; filters and search input remain steady. The
/// opacity settles after the data update, avoiding animated row reordering.
struct SearchRefreshAppearance: ViewModifier {
    let state: SearchResultsState
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var opacity = 1.0

    func body(content: Content) -> some View {
        content
            .opacity(opacity)
            .onAppear { opacity = state.isConfirmed ? 1 : 0.72 }
            .onChange(of: state.isConfirmed) { confirmed in
                withAnimation(reduceMotion ? nil : .easeOut(duration: 0.18)) {
                    opacity = confirmed ? 1 : 0.72
                }
            }
    }
}


/// Retained empty results must not offer recovery for an unconfirmed query.
struct SearchEmptyCard: View {
    let resolution: SearchEmptyState
    let state: SearchResultsState
    let recover: (SearchEmptyRecovery) -> Void

    var body: some View {
        EmptyCard(
            title: state.isConfirmed ? resolution.title : "No previous results",
            message: state.isConfirmed ? resolution.message : "Results for your updated search will appear here.",
            actionTitle: state.isConfirmed ? resolution.actionTitle : nil,
            action: state.isConfirmed ? resolution.recovery.map { recovery in { recover(recovery) } } : nil
        )
    }
}
