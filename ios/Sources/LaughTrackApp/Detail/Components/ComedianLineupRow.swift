import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ComedianLineupRow: View {
    let comedian: Components.Schemas.ComedianLineup
    let apiClient: Client
    @Binding var feedbackMessage: String?
    let openDetail: () -> Void

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme

    var body: some View {
        let isFavorite = favorites.value(for: comedian.uuid, fallback: comedian.isFavorite)

        HStack(spacing: theme.spacing.sm) {
            Button(action: openDetail) {
                LaughTrackResultRow(
                    title: comedian.name,
                    subtitle: nil,
                    metadata: ["\(comedian.showCount ?? 0) upcoming shows"],
                    systemImage: "music.mic",
                    imageURL: comedian.imageUrl,
                    showsDisclosureIndicator: false
                )
            }
            .buttonStyle(.plain)

            FavoriteButton(
                isFavorite: isFavorite,
                isPending: favorites.isPending(comedian.uuid)
            ) {
                let result = await favorites.toggle(
                    uuid: comedian.uuid,
                    currentValue: isFavorite,
                    apiClient: apiClient,
                    authManager: authManager
                )
                switch result {
                case .updated(let next):
                    feedbackMessage = FavoriteFeedback.message(for: comedian.name, isFavorite: next)
                case .signInRequired:
                    loginModalPresenter.present()
                case .failure(let message):
                    feedbackMessage = message
                }
            }
        }
    }
}
