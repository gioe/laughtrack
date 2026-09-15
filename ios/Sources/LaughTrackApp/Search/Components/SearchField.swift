import SwiftUI
import LaughTrackBridge

struct SearchField: View {
    @Environment(\.appTheme) private var theme
    @FocusState private var isFocused: Bool

    let title: String
    let prompt: String
    @Binding var text: String
    var showsTitle: Bool = true
    var accessibilityIdentifier: String?
    var showsClearButton = false
    var focusContext = ""

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.xs) {
            if showsTitle {
                Text(title)
                    .font(theme.laughTrackTokens.typography.eyebrow)
                    .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                    .textCase(.uppercase)
            }

            LaughTrackSearchField(
                placeholder: prompt,
                text: $text,
                accessibilityIdentifier: accessibilityIdentifier,
                focus: $isFocused
            ) {
                if showsClearButton {
                    Button {
                        text = ""
                        isFocused = true
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 18))
                            .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                            .frame(width: 44, height: 44)
                    }
                    .buttonStyle(.plain)
                    .opacity(text.isEmpty ? 0 : 1)
                    .disabled(text.isEmpty)
                    .accessibilityHidden(text.isEmpty)
                    .accessibilityLabel("Clear \(title.lowercased())")
                    .accessibilityIdentifier("\(accessibilityIdentifier ?? "search").clear")
                }
            }
                .modifier(SearchFieldInputBehavior())
                .submitLabel(.search)
                .onSubmit { isFocused = false }
        }
        .onChange(of: focusContext) { _ in isFocused = false }
        .onDisappear { isFocused = false }
    }
}
