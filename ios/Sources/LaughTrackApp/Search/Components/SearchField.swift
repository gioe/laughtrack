import SwiftUI
import LaughTrackBridge

struct SearchField: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let prompt: String
    @Binding var text: String

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.xs) {
            Text(title)
                .font(theme.laughTrackTokens.typography.eyebrow)
                .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                .textCase(.uppercase)

            LaughTrackSearchField(placeholder: prompt, text: $text)
                .modifier(SearchFieldInputBehavior())
        }
    }
}
