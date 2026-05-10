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
        let laughTrack = theme.laughTrackTokens
        let isFavorite = favorites.value(for: comedian.uuid, fallback: comedian.isFavorite)
        let isPending = favorites.isPending(comedian.uuid)

        HStack(spacing: theme.spacing.md) {
            Button(action: openDetail) {
                HStack(spacing: theme.spacing.md) {
                    artwork

                    Text(comedian.name)
                        .font(laughTrack.typography.cardTitle)
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .lineLimit(2)
                        .multilineTextAlignment(.leading)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            Button {
                Task {
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
            } label: {
                ZStack {
                    if isPending {
                        ProgressView()
                            .progressViewStyle(.circular)
                            .tint(laughTrack.colors.accent)
                    } else {
                        Image(systemName: isFavorite ? "heart.fill" : "heart")
                            .font(.system(size: theme.iconSizes.md, weight: .semibold))
                            .foregroundStyle(isFavorite ? laughTrack.colors.accentStrong : laughTrack.colors.textSecondary)
                    }
                }
                .frame(width: 44, height: 44)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .disabled(isPending)
            .accessibilityLabel(isFavorite ? "Remove favorite" : "Add favorite")
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens
        let url = URL.normalizedExternalURL(comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines))

        Group {
            if let url {
                CachedAsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    Circle()
                        .fill(laughTrack.colors.surfaceMuted)
                        .overlay {
                            ProgressView()
                                .tint(laughTrack.colors.accent)
                        }
                } error: { _ in
                    fallbackArtwork
                }
            } else {
                fallbackArtwork
            }
        }
        .frame(width: 56, height: 56)
        .clipShape(Circle())
    }

    private var fallbackArtwork: some View {
        let laughTrack = theme.laughTrackTokens

        return Circle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "music.mic")
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }
}
