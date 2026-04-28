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
                        subtitle: content.upcomingShows.isEmpty ? "No upcoming shows" : "\(content.upcomingShows.count) upcoming show\(content.upcomingShows.count == 1 ? "" : "s")",
                        imageURL: comedian.imageUrl,
                        badges: comedianHeroBadges(comedian: comedian, upcomingShowCount: content.upcomingShows.count)
                    )

                    LaughTrackCard(tone: .muted) {
                        VStack(alignment: .leading, spacing: 12) {
                            LaughTrackSectionHeader(
                                eyebrow: "Saved comics",
                                title: "Favorite",
                                subtitle: "Save this comic to find them again later."
                            )
                            HStack {
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(isFavorite ? "In your favorites" : "Not saved yet")
                                        .font(theme.laughTrackTokens.typography.cardTitle)
                                        .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                                    Text("Tap the heart to save or unsave this comic.")
                                        .font(theme.laughTrackTokens.typography.body)
                                        .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                                }
                                Spacer()
                                FavoriteButton(
                                    isFavorite: isFavorite,
                                    isPending: favorites.isPending(comedian.uuid)
                                ) {
                                    await toggleFavorite(name: comedian.name, uuid: comedian.uuid, currentValue: isFavorite)
                                }
                            }
                        }
                    }

                    DetailInfoCard(
                        eyebrow: "Profile",
                        title: "About this comedian",
                        subtitle: "Basic info and links.",
                        rows: comedianProfileRows(comedian: comedian, upcomingShowCount: content.upcomingShows.count)
                    )

                    SocialLinkSection(socialData: comedian.socialData) { url in
                        openURL(url)
                    }

                    LaughTrackCard {
                        VStack(alignment: .leading, spacing: 12) {
                            LaughTrackSectionHeader(
                                eyebrow: "Upcoming shows",
                                title: "Catch them live",
                                subtitle: "Upcoming dates for this comedian."
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
                                title: "People sharing the bill",
                                subtitle: "When lineup data is available, you can hop straight into the next comedian detail page."
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

    private func comedianHeroBadges(
        comedian: Components.Schemas.ComedianDetail,
        upcomingShowCount: Int
    ) -> [DetailHeroBadge] {
        var badges: [DetailHeroBadge] = []

        if upcomingShowCount > 0 {
            badges.append(
                DetailHeroBadge(
                    title: "\(upcomingShowCount) upcoming",
                    systemImage: "calendar",
                    tone: .neutral
                )
            )
        }

        if let audienceReach = audienceReachText(for: comedian.socialData) {
            badges.append(
                DetailHeroBadge(
                    title: audienceReach,
                    systemImage: "person.3.fill",
                    tone: .accent
                )
            )
        }

        if let website = comedian.socialData.website, !website.isEmpty {
            badges.append(
                DetailHeroBadge(
                    title: "Website on file",
                    systemImage: "link",
                    tone: .neutral
                )
            )
        }

        return badges
    }

    private func comedianProfileRows(
        comedian: Components.Schemas.ComedianDetail,
        upcomingShowCount: Int
    ) -> [DetailInfoRow] {
        [
            DetailInfoRow(label: "Upcoming", value: upcomingShowCount == 0 ? "No upcoming dates yet" : "\(upcomingShowCount) shows"),
            DetailInfoRow(label: "Audience", value: audienceReachText(for: comedian.socialData)),
            DetailInfoRow(label: "Instagram", value: socialHandle(comedian.socialData.instagramAccount, prefix: "@")),
            DetailInfoRow(label: "TikTok", value: socialHandle(comedian.socialData.tiktokAccount, prefix: "@")),
            DetailInfoRow(label: "YouTube", value: socialHandle(comedian.socialData.youtubeAccount, prefix: "@")),
            DetailInfoRow(label: "Website", value: comedian.socialData.website),
            DetailInfoRow(label: "Linktree", value: comedian.socialData.linktree)
        ]
    }

    private func audienceReachText(for socialData: Components.Schemas.SocialData) -> String? {
        let followerCount =
            (socialData.instagramFollowers ?? 0) +
            (socialData.tiktokFollowers ?? 0) +
            (socialData.youtubeFollowers ?? 0)

        guard followerCount > 0 else { return nil }
        return "\(followerCount.formatted(.number.notation(.compactName))) followers"
    }

    private func socialHandle(_ handle: String?, prefix: String) -> String? {
        guard let handle, !handle.isEmpty else { return nil }
        return handle.hasPrefix(prefix) ? handle : "\(prefix)\(handle)"
    }
}
