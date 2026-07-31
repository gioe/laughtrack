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
    @State private var pinnedShowsTodayRequest = 0

    private static let pinnedShowsAnchor = "club-detail-pinned-shows"

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
                let marqueeRows: [ClubDetailMarqueeRow] = {
                    guard case .success(let highlights) = highlightsModel.phase else { return [] }
                    return ClubDetailHighlightsPresentation.marqueeRows(from: highlights)
                }()
                ScrollViewReader { proxy in
                    ScrollView {
                        AdaptiveDetailCatalogLayout {
                            VStack(spacing: ClubVenueMarqueeStyle.artworkToBoardSpacing) {
                                MarqueeHero(
                                    title: club.name,
                                    imageURL: ClubDetailHeroPresentation.imageURL(for: club) ?? "",
                                    thumbnailStyle: .clubMarquee,
                                    actions: clubHeroActions(club: club),
                                    actionPlacement: .belowTitle,
                                    actionStyle: .compactPill,
                                    bottomPadding: 0,
                                    openURL: { url in
                                        openURL(url)
                                    },
                                    fallbackSystemImage: ArtworkFallbackKind.club.systemImage
                                )

                                if !marqueeRows.isEmpty {
                                    ClubDetailTonightMarqueeSection(
                                        rows: marqueeRows,
                                        openShow: { show in
                                            coordinator.open(.show(show.id))
                                        },
                                        showAll: {
                                            pinnedShowsTodayRequest += 1
                                            withAnimation {
                                                proxy.scrollTo(
                                                    Self.pinnedShowsAnchor,
                                                    anchor: .top
                                                )
                                            }
                                        }
                                    )
                                    .padding(.horizontal, 8)
                                }
                            }
                        } content: {
                            VStack(alignment: .leading, spacing: 20) {
                                if case .success(let highlights) = highlightsModel.phase {
                                    if marqueeRows.isEmpty, let nextShow = highlights.nextShow {
                                        ClubDetailShowHighlightSection(
                                            featuredShow: .init(title: "Next up", show: nextShow)
                                        ) {
                                            coordinator.open(.show(nextShow.id))
                                        }
                                    }

                                }

                                PinnedShowsList(
                                    apiClient: apiClient,
                                    nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self),
                                    pinnedClubName: club.name,
                                    todayRequest: pinnedShowsTodayRequest
                                )
                                .id(Self.pinnedShowsAnchor)

                                if case .success(let highlights) = highlightsModel.phase,
                                   !highlights.frequentPerformers.isEmpty {
                                    ClubDetailFrequentPerformersSection(
                                        performers: highlights.frequentPerformers,
                                        openPerformer: { performer in
                                            coordinator.open(.comedian(performer.id))
                                        }
                                    )
                                }
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, theme.spacing.lg)
                        }
                    }
                    .modifier(DetailAtmosphereScrollContent())
                }
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
    @MainActor
    static func marqueeRows(
        from highlights: Components.Schemas.ClubHighlights
    ) -> [ClubDetailMarqueeRow] {
        highlights.tonightShows
            .map { show in
                let comedian = ShowRow.topLineup(for: show, limit: 1).first
                return ClubDetailMarqueeRow(
                    show: show,
                    performerName: comedian?.name ?? ShowTitlePresentation.title(for: show),
                    localizedStartTime: ShowFormatting.dateStack(
                        show.date,
                        timezoneID: show.timezone
                    ).time,
                    performerPopularity: comedian?.socialData?.popularity ?? -1,
                    performerShowCount: comedian?.showCount ?? 0
                )
            }
            .sorted(by: ranksBefore)
            .prefix(3)
            .sorted(by: displaysBefore)
    }

    private static func ranksBefore(
        _ lhs: ClubDetailMarqueeRow,
        _ rhs: ClubDetailMarqueeRow
    ) -> Bool {
        if lhs.performerPopularity != rhs.performerPopularity {
            return lhs.performerPopularity > rhs.performerPopularity
        }
        if lhs.performerShowCount != rhs.performerShowCount {
            return lhs.performerShowCount > rhs.performerShowCount
        }
        return displaysBefore(lhs, rhs)
    }

    private static func displaysBefore(
        _ lhs: ClubDetailMarqueeRow,
        _ rhs: ClubDetailMarqueeRow
    ) -> Bool {
        if lhs.show.date != rhs.show.date {
            return lhs.show.date < rhs.show.date
        }
        return lhs.show.id < rhs.show.id
    }
}

struct ClubDetailMarqueeRow: Hashable {
    let show: Components.Schemas.Show
    let performerName: String
    let localizedStartTime: String
    fileprivate let performerPopularity: Double
    fileprivate let performerShowCount: Int
}

private struct ClubDetailTonightMarqueeSection: View {
    let rows: [ClubDetailMarqueeRow]
    let openShow: (Components.Schemas.Show) -> Void
    let showAll: () -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        VStack(spacing: 0) {
            Text("Tonight")
                .font(.system(.subheadline, design: .rounded, weight: .heavy))
                .tracking(1.4)
                .textCase(.uppercase)
                .foregroundStyle(ClubVenueMarqueeStyle.paper)
                .padding(.horizontal, theme.spacing.lg)
                .padding(.vertical, theme.spacing.sm)
                .background(ClubVenueMarqueeStyle.outline)
                .clipShape(
                    RoundedRectangle(
                        cornerRadius: ClubVenueMarqueeStyle.cornerRadius,
                        style: .continuous
                    )
                )
                .overlay {
                    RoundedRectangle(
                        cornerRadius: ClubVenueMarqueeStyle.cornerRadius,
                        style: .continuous
                    )
                    .stroke(ClubVenueMarqueeStyle.outline, lineWidth: 1.5)
                }

            ForEach(Array(rows.enumerated()), id: \.element.show.id) { index, row in
                if index > 0 {
                    Divider()
                        .overlay(Color.black.opacity(0.24))
                        .padding(.horizontal, theme.spacing.md)
                }

                Button {
                    openShow(row.show)
                } label: {
                    HStack(alignment: .firstTextBaseline, spacing: theme.spacing.md) {
                        Text(row.performerName.uppercased())
                            .font(.system(.headline, design: .monospaced, weight: .bold))
                            .multilineTextAlignment(.leading)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        Text(row.localizedStartTime.uppercased())
                            .font(.system(.subheadline, design: .monospaced, weight: .semibold))
                            .lineLimit(1)

                        Image(systemName: "chevron.right")
                            .font(.caption.weight(.bold))
                    }
                    .foregroundStyle(Color.black)
                    .padding(.horizontal, theme.spacing.lg)
                    .padding(.vertical, theme.spacing.md)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("\(row.performerName), \(row.localizedStartTime)")
                .accessibilityIdentifier(
                    LaughTrackViewTestID.clubDetailHighlightShowButton(row.show.id)
                )
            }

            Button(action: showAll) {
                Text("Show all")
                    .font(.system(.subheadline, design: .monospaced, weight: .bold))
                    .foregroundStyle(Color.black)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, theme.spacing.sm)
            }
            .buttonStyle(.plain)
            .overlay(alignment: .top) {
                Divider().overlay(Color.black.opacity(0.3))
            }
            .accessibilityHint("Shows every performance at this club today")
        }
        .background(ClubVenueMarqueeStyle.paper)
        .clipShape(
            RoundedRectangle(
                cornerRadius: ClubVenueMarqueeStyle.cornerRadius,
                style: .continuous
            )
        )
        .overlay {
            RoundedRectangle(
                cornerRadius: ClubVenueMarqueeStyle.cornerRadius,
                style: .continuous
            )
                .stroke(ClubVenueMarqueeStyle.outline, lineWidth: 1.5)
        }
        .overlay {
            RoundedRectangle(
                cornerRadius: ClubVenueMarqueeStyle.cornerRadius,
                style: .continuous
            )
                .inset(by: 6)
                .stroke(
                    ClubVenueMarqueeStyle.bulbColor,
                    style: ClubVenueMarqueeStyle.bulbStroke
                )
                .shadow(color: ClubVenueMarqueeStyle.bulbColor.opacity(0.18), radius: 2)
                .allowsHitTesting(false)
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier(LaughTrackViewTestID.clubDetailHighlightSection)
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
                title: "Directions",
                systemImage: "map.fill",
                url: URL.mapsURL(for: club.address)
            )
        ]
    }
}
