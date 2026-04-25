import SwiftUI
import LaughTrackBridge

struct AuthLoadingView: View {
    @Environment(\.appTheme) private var theme

    let message: String

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(spacing: laughTrack.spacing.sectionGap) {
            LaughTrackCard(tone: .accent) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    Text("LaughTrack account")
                        .font(laughTrack.typography.eyebrow)
                        .foregroundStyle(laughTrack.colors.textInverse.opacity(0.78))
                        .textCase(.uppercase)
                    Text("Signing you in with the shared token flow.")
                        .font(laughTrack.typography.screenTitle)
                        .foregroundStyle(laughTrack.colors.textInverse)
                    Text("The browser handoff and session exchange stay the same; this screen now uses the same branded cards and typography as the rest of the app.")
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textInverse.opacity(0.92))
                }
            }

            LaughTrackStateView(
                tone: .loading,
                title: "Loading LaughTrack",
                message: message
            )
        }
        .padding(theme.spacing.xl)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
    }
}
