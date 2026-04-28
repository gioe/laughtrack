import SwiftUI
import LaughTrackBridge
import LaughTrackCore

struct SessionBannerCard: View {
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme

    let signedOutMessage: String?

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button {
            if authManager.currentSession == nil {
                loginModalPresenter.present()
            }
        } label: {
            LaughTrackCard(density: .compact) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    Text(authManager.currentSession == nil ? "Browsing as guest" : "Signed in")
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                        .textCase(.uppercase)

                    if let session = authManager.currentSession {
                        Text(session.provider?.displayName ?? "Saved mobile session")
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                        Text(
                            session.expiresAt.map {
                                "Favorite actions are enabled. Your session expires \($0.formatted(.dateTime.month().day().hour().minute()))."
                            } ?? "Favorite actions are enabled for this session."
                        )
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                    } else {
                        Text("Browsing stays open even when you’re signed out.")
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                        Text(signedOutMessage ?? "Open Settings when you want to connect Apple or Google, sync favorites, and recover quickly if sign-in is interrupted.")
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                    }
                }
            }
        }
        .buttonStyle(.plain)
        .disabled(authManager.currentSession != nil)
    }
}
