import SwiftUI

struct ActivityView: View {
    static let title = "Activity"
    static let emptyStateMessage = "Alerts and reminders will appear here."

    @Environment(\.appTheme) private var theme

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            Text(Self.title)
                .font(theme.laughTrackTokens.typography.screenTitle)
                .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)

            Text(Self.emptyStateMessage)
                .font(theme.laughTrackTokens.typography.body)
                .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .padding(theme.spacing.xl)
        .accessibilityIdentifier(LaughTrackViewTestID.activityTabScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .navigationTitle(Self.title)
        .modifier(LaughTrackNavigationChrome(background: theme.laughTrackTokens.colors.canvas))
    }
}
