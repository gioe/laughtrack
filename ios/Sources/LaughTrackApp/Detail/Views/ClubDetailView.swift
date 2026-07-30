import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ClubDetailView: View {
    let clubId: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @EnvironmentObject private var clubFavorites: ClubFavoriteStore
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL
    @Environment(\.serviceContainer) private var serviceContainer
    @StateObject private var model: ClubDetailModel
    @StateObject private var highlightsModel: ClubHighlightsModel
    @State private var feedbackMessage: String?

    init(clubId: Int, apiClient: Client) {
        self.clubId = clubId
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: ClubDetailModel(clubId: clubId))
        _highlightsModel = StateObject(wrappedValue: ClubHighlightsModel(clubId: clubId))
    }

    var body: some View {
        Group {
            switch model.phase {
            case .idle, .loading:
                CalendarDetailSkeleton()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.reload(apiClient: apiClient, cache: detailCache) },
                    signIn: { coordinator.push(.profile) }
                )
                .padding()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .success(let content):
                let club = content.club
                ScrollView {
                    AdaptiveDetailCatalogLayout {
                        MarqueeHero(
                            title: club.name,
                            imageURL: ClubDetailHeroPresentation.imageURL(for: club) ?? "",
                            thumbnailStyle: .clubMarquee,
                            actions: clubHeroActions(club: club),
                            openURL: { url in
                                openURL(url)
                            },
                            fallbackSystemImage: ArtworkFallbackKind.club.systemImage
                        )
                    } content: {
                        VStack(alignment: .leading, spacing: 20) {
                            if case .success(let highlights) = highlightsModel.phase {
                                if let featuredShow = ClubDetailHighlightsPresentation.featuredShow(
                                    from: highlights
                                ) {
                                    ClubDetailShowHighlightSection(featuredShow: featuredShow) {
                                        coordinator.open(.show(featuredShow.show.id))
                                    }
                                }

                                if !highlights.frequentPerformers.isEmpty {
                                    ClubDetailFrequentPerformersSection(
                                        performers: highlights.frequentPerformers,
                                        openPerformer: { performer in
                                            coordinator.open(.comedian(performer.id))
                                        }
                                    )
                                }
                            }

                            PinnedShowsList(
                                apiClient: apiClient,
                                nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self),
                                pinnedClubName: club.name
                            )
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, theme.spacing.lg)
                    }
                }
                .modifier(DetailAtmosphereScrollContent())
            }
        }
        .ignoresSafeArea(.container, edges: .top)
        .accessibilityIdentifier(LaughTrackViewTestID.clubDetailScreen)
        .modifier(DetailAtmosphereRouteBackground())
        .overlay(alignment: .top) {
            DetailChromeBar(
                onBack: { coordinator.pop() },
                onHome: coordinator.detailHomeAction,
                favoriteState: clubFavoriteState
            )
        }
        .modifier(EntityDetailNavigationChrome(
            entity: .club,
            title: navigationTitle,
            favoriteState: clubFavoriteState
        ))
        .task {
            await model.loadIfNeeded(apiClient: apiClient, cache: detailCache)
        }
        .task {
            await highlightsModel.loadIfNeeded(apiClient: apiClient)
        }
        .alert("LaughTrack", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
    }

    private func clubHeroActions(club: Components.Schemas.ClubDetail) -> [DetailHeroAction] {
        ClubDetailHeroPresentation.actions(for: club)
    }

    private var detailCache: DataCache<LaughTrackCacheKey> {
        serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
    }

    private func toggleFavorite(clubId: Int, name: String, currentValue: Bool) async {
        let result = await clubFavorites.toggle(
            clubId: clubId,
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

    private var navigationTitle: String {
        if case .success(let content) = model.phase {
            return content.club.name
        }
        return ""
    }

    private var clubFavoriteState: DetailFavoriteState? {
        guard case .success(let content) = model.phase else { return nil }
        let club = content.club
        let isFavorite = clubFavorites.value(for: club.id)
        return DetailFavoriteState(
            isFavorite: isFavorite,
            isPending: clubFavorites.isPending(club.id),
            action: {
                await toggleFavorite(
                    clubId: club.id,
                    name: club.name,
                    currentValue: isFavorite
                )
            }
        )
    }
}

struct ClubDetailFeaturedShow: Hashable {
    let title: String
    let show: Components.Schemas.Show
}

enum ClubDetailHighlightsPresentation {
    static func featuredShow(
        from highlights: Components.Schemas.ClubHighlights
    ) -> ClubDetailFeaturedShow? {
        if let tonight = highlights.tonightShows.first {
            return ClubDetailFeaturedShow(title: "Tonight", show: tonight)
        }
        if let next = highlights.nextShow {
            return ClubDetailFeaturedShow(title: "Next up", show: next)
        }
        return nil
    }
}

private struct ClubDetailShowHighlightSection: View {
    let featuredShow: ClubDetailFeaturedShow
    let openShow: () -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            Text(featuredShow.title)
                .font(laughTrack.typography.sectionTitle)
                .foregroundStyle(laughTrack.colors.textPrimary)
                .accessibilityIdentifier(LaughTrackViewTestID.clubDetailHighlightSection)

            Button(action: openShow) {
                HomeShowsTonightHeroCard(
                    show: featuredShow.show,
                    width: nil,
                    artworkHeight: 150
                )
                    .padding(theme.spacing.md)
                    .frame(maxWidth: .infinity)
                    .background(laughTrack.colors.surface)
                    .overlay(
                        RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                            .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                    )
                    .clipShape(
                        RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                    )
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier(
                LaughTrackViewTestID.clubDetailHighlightShowButton(featuredShow.show.id)
            )
        }
    }
}

private struct ClubDetailFrequentPerformersSection: View {
    let performers: [Components.Schemas.ComedianListItem]
    let openPerformer: (Components.Schemas.ComedianListItem) -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            Text("Frequently on this stage")
                .font(laughTrack.typography.sectionTitle)
                .foregroundStyle(laughTrack.colors.textPrimary)
                .accessibilityIdentifier(
                    LaughTrackViewTestID.clubDetailFrequentPerformersSection
                )

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: theme.spacing.sm) {
                    ForEach(performers, id: \.uuid) { performer in
                        Button {
                            openPerformer(performer)
                        } label: {
                            HomeTrendingComedianCard(
                                comedian: performer,
                                stageHeight: 112
                            )
                                .frame(width: 156)
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier(
                            LaughTrackViewTestID.clubDetailPerformerButton(performer.id)
                        )
                    }
                }
            }
        }
    }
}

enum ClubDetailHeroPresentation {
    static func imageURL(for club: Components.Schemas.ClubDetail) -> String? {
        let hero = club.heroImageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        if !hero.isEmpty { return hero }
        let logo = club.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        return logo.isEmpty ? nil : logo
    }

    static func actions(for club: Components.Schemas.ClubDetail) -> [DetailHeroAction] {
        [
            DetailHeroAction(
                title: "Website",
                systemImage: "arrow.up.right",
                url: URL.normalizedExternalURL(club.website)
            ),
            DetailHeroAction(
                title: "Maps",
                systemImage: "map.fill",
                url: URL.mapsURL(for: club.address)
            )
        ]
    }
}
