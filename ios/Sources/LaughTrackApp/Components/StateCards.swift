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

    init(title: String = "Nothing here yet", message: String) {
        self.title = title
        self.message = message
    }

    var body: some View {
        LaughTrackInlineStateCard(
            tone: .empty,
            title: title,
            message: message
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

    let count: Int
    let total: Int

    var body: some View {
        LaughTrackContextRow(leading: "Showing \(count) of \(total)")
    }
}
