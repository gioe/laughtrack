import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ComedianDetailView: View {
    let comedianID: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL

    @StateObject private var model: ComedianDetailModel
    @State private var feedbackMessage: String?

    init(comedianID: Int, apiClient: Client) {
        self.comedianID = comedianID
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: ComedianDetailModel(comedianID: comedianID))
    }

    var body: some View {
        ScrollView {
            switch model.phase {
            case .idle, .loading:
                LoadingCard()
                    .padding()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.reload(apiClient: apiClient, favorites: favorites) },
                    signIn: { coordinator.push(.profile) }
                )
                .padding()
            case .success(let content):
                let comedian = content.comedian
                let isFavorite = favorites.value(for: comedian.uuid)
                VStack(alignment: .leading, spacing: 20) {
                    DetailHero(
                        title: comedian.name,
                        subtitle: nil,
                        imageURL: comedian.imageUrl,
                        badges: []
                    )

                    ComedianHeroActionRow(
                        isFavorite: isFavorite,
                        isFavoritePending: favorites.isPending(comedian.uuid),
                        socialLinks: socialActionLinks(from: comedian.socialData),
                        toggleFavorite: {
                            await toggleFavorite(name: comedian.name, uuid: comedian.uuid, currentValue: isFavorite)
                        },
                        openURL: { url in
                            openURL(url)
                        }
                    )

                    ComedianHighlightsRow(
                        highlights: comedianHighlights(
                            comedian: comedian,
                            upcomingShows: content.upcomingShows
                        ),
                        openURL: { url in
                            openURL(url)
                        }
                    )

                    LaughTrackCard {
                        VStack(alignment: .leading, spacing: 12) {
                            LaughTrackSectionHeader(
                                eyebrow: "Upcoming shows",
                                title: "Catch them live"
                            )

                            if let relatedContentMessage = content.relatedContentMessage {
                                InlineStatusMessage(message: relatedContentMessage)
                            }

                            if content.upcomingShows.isEmpty {
                                EmptyCard(message: "No upcoming shows are available for this comedian right now.")
                            } else {
                                ForEach(content.upcomingShows, id: \.id) { show in
                                    Button {
                                        coordinator.open(.show(show.id))
                                    } label: {
                                        ShowRow(show: show)
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }
                    }

                    LaughTrackCard(tone: .muted) {
                        VStack(alignment: .leading, spacing: 12) {
                            LaughTrackSectionHeader(
                                eyebrow: "Related comedians",
                                title: "People sharing the bill"
                            )

                            if content.relatedComedians.isEmpty {
                                EmptyCard(message: "No related comedians are available yet.")
                            } else {
                                ForEach(content.relatedComedians, id: \.uuid) { relatedComedian in
                                    ComedianLineupRow(
                                        comedian: relatedComedian,
                                        apiClient: apiClient,
                                        feedbackMessage: $feedbackMessage,
                                        openDetail: { coordinator.open(.comedian(relatedComedian.id)) }
                                    )
                                }
                            }
                        }
                    }
                }
                .padding()
            }
        }
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .accessibilityIdentifier(LaughTrackViewTestID.comedianDetailScreen)
        .navigationTitle("Comedian")
        .modifier(InlineNavigationTitle())
        .task {
            await model.loadIfNeeded(apiClient: apiClient, favorites: favorites)
        }
        .alert("LaughTrack", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
    }

    private func socialActionLinks(from socialData: Components.Schemas.SocialData) -> [SocialLink] {
        SocialLink.links(from: socialData).filter { $0.label != "Website" }
    }

    private func comedianHighlights(
        comedian: Components.Schemas.ComedianDetail,
        upcomingShows: [Components.Schemas.Show]
    ) -> [ComedianHighlight] {
        [
            nextShowHighlight(from: upcomingShows.first),
            audienceReachText(for: comedian.socialData).map {
                ComedianHighlight(title: $0, systemImage: "person.3.fill", tone: .accent)
            },
            URL.normalizedExternalURL(comedian.socialData.website).map {
                ComedianHighlight(title: "Website", systemImage: "safari", tone: .neutral, url: $0)
            }
        ]
        .compactMap { $0 }
    }

    private func nextShowHighlight(from show: Components.Schemas.Show?) -> ComedianHighlight? {
        guard let show else { return nil }

        let location = nextShowLocation(from: show)
        let title: String
        if let location {
            title = "\(ShowFormatting.listDate(show.date)) · \(location)"
        } else {
            title = ShowFormatting.listDate(show.date)
        }

        return ComedianHighlight(title: title, systemImage: "calendar", tone: .highlight)
    }

    private func nextShowLocation(from show: Components.Schemas.Show) -> String? {
        if let address = show.address {
            let components = address
                .split(separator: ",")
                .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.isEmpty }

            if components.count >= 3 {
                let city = components[components.count - 2]
                let state = components.last?.split(separator: " ").first.map(String.init)
                return [city, state].compactMap { $0 }.joined(separator: ", ")
            }
        }

        return show.clubName
    }

    private func toggleFavorite(name: String, uuid: String, currentValue: Bool) async {
        let result = await favorites.toggle(
            uuid: uuid,
            currentValue: currentValue,
            apiClient: apiClient,
            authManager: authManager
        )

        switch result {
        case .updated(let next):
            feedbackMessage = FavoriteFeedback.message(for: name, isFavorite: next)
        case .signInRequired:
            loginModalPresenter.present()
        case .failure(let message):
            feedbackMessage = message
        }
    }

    private func audienceReachText(for socialData: Components.Schemas.SocialData) -> String? {
        let followerCount =
            (socialData.instagramFollowers ?? 0) +
            (socialData.tiktokFollowers ?? 0) +
            (socialData.youtubeFollowers ?? 0)

        guard followerCount > 0 else { return nil }
        return "\(followerCount.formatted(.number.notation(.compactName))) followers"
    }
}

private struct ComedianHighlight: Identifiable {
    let id = UUID()
    let title: String
    let systemImage: String
    let tone: LaughTrackBadgeTone
    let url: URL?

    init(
        title: String,
        systemImage: String,
        tone: LaughTrackBadgeTone,
        url: URL? = nil
    ) {
        self.title = title
        self.systemImage = systemImage
        self.tone = tone
        self.url = url
    }
}

private struct ComedianHeroActionRow: View {
    @Environment(\.appTheme) private var theme

    let isFavorite: Bool
    let isFavoritePending: Bool
    let socialLinks: [SocialLink]
    let toggleFavorite: () async -> Void
    let openURL: (URL) -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: theme.spacing.sm) {
                ComedianFavoriteActionButton(
                    isFavorite: isFavorite,
                    isPending: isFavoritePending,
                    action: toggleFavorite
                )

                ForEach(socialLinks) { link in
                    ComedianSocialActionButton(link: link) {
                        openURL(link.url)
                    }
                }
            }
            .padding(.vertical, theme.spacing.xs)
        }
    }
}

private struct ComedianHighlightsRow: View {
    @Environment(\.appTheme) private var theme

    let highlights: [ComedianHighlight]
    let openURL: (URL) -> Void

    var body: some View {
        if !highlights.isEmpty {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: theme.spacing.sm) {
                    ForEach(highlights) { highlight in
                        if let url = highlight.url {
                            Button {
                                openURL(url)
                            } label: {
                                LaughTrackBadge(
                                    highlight.title,
                                    systemImage: highlight.systemImage,
                                    tone: highlight.tone
                                )
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel("Open \(highlight.title)")
                        } else {
                            LaughTrackBadge(
                                highlight.title,
                                systemImage: highlight.systemImage,
                                tone: highlight.tone
                            )
                        }
                    }
                }
                .padding(.vertical, theme.spacing.xs)
            }
        }
    }
}

private struct ComedianFavoriteActionButton: View {
    @Environment(\.appTheme) private var theme

    let isFavorite: Bool
    let isPending: Bool
    let action: () async -> Void

    var body: some View {
        Button {
            Task {
                await action()
            }
        } label: {
            HStack(spacing: theme.spacing.xs) {
                if isPending {
                    ProgressView()
                        .progressViewStyle(.circular)
                        .frame(width: 18, height: 18)
                } else {
                    Image(systemName: isFavorite ? "heart.fill" : "heart")
                        .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                }

                Text(isFavorite ? "Saved" : "Save")
                    .font(theme.laughTrackTokens.typography.metadata)
                    .lineLimit(1)
            }
            .foregroundStyle(isFavorite ? theme.laughTrackTokens.colors.accentStrong : theme.laughTrackTokens.colors.textPrimary)
            .padding(.horizontal, theme.spacing.md)
            .padding(.vertical, theme.spacing.xs)
            .background(
                Capsule(style: .continuous)
                    .fill(isFavorite ? theme.laughTrackTokens.colors.accentMuted.opacity(0.45) : theme.laughTrackTokens.colors.canvas)
            )
            .overlay(
                Capsule(style: .continuous)
                    .stroke(isFavorite ? theme.laughTrackTokens.colors.accentStrong.opacity(0.35) : theme.laughTrackTokens.colors.borderStrong.opacity(0.5), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel(isFavorite ? "Remove favorite" : "Add favorite")
    }
}

private struct ComedianSocialActionButton: View {
    @Environment(\.appTheme) private var theme

    let link: SocialLink
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: theme.spacing.xs) {
                Image(systemName: systemImage)
                    .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                Text(link.label)
                    .font(theme.laughTrackTokens.typography.metadata)
                    .lineLimit(1)
            }
            .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
            .padding(.horizontal, theme.spacing.md)
            .padding(.vertical, theme.spacing.xs)
            .background(
                Capsule(style: .continuous)
                    .fill(theme.laughTrackTokens.colors.canvas)
            )
            .overlay(
                Capsule(style: .continuous)
                    .stroke(theme.laughTrackTokens.colors.borderStrong.opacity(0.5), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Open \(link.label)")
    }

    private var systemImage: String {
        switch link.label {
        case "Instagram":
            return "camera"
        case "TikTok":
            return "music.note"
        case "YouTube":
            return "play.rectangle.fill"
        case "Website":
            return "safari"
        default:
            return "link"
        }
    }
}
