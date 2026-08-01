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
                let eveningSummary: ClubDetailEveningSummary? = {
                    guard case .success(let highlights) = highlightsModel.phase else { return nil }
                    return ClubDetailHighlightsPresentation.eveningSummary(from: highlights)
                }()
                ScrollView {
                    AdaptiveDetailCatalogLayout {
                        VStack(spacing: ClubVenueMarqueeStyle.artworkToBoardSpacing) {
                            MarqueeHero(
                                title: club.name,
                                imageURL: ClubDetailHeroPresentation.imageURL(for: club) ?? "",
                                thumbnailStyle: .clubMarquee,
                                // Set to true to restore venue artwork above the Tonight marquee.
                                showsThumbnail: false,
                                actions: clubHeroActions(club: club),
                                actionPlacement: .belowTitle,
                                actionStyle: .compactPill,
                                bottomPadding: 0,
                                openURL: { url in
                                    openURL(url)
                                },
                                fallbackSystemImage: ArtworkFallbackKind.club.systemImage
                            )

                            if let eveningSummary {
                                ClubDetailTonightMarqueeSection(
                                    summary: eveningSummary
                                )
                                .padding(.horizontal, 8)
                            }
                        }
                    } content: {
                        VStack(alignment: .leading, spacing: 20) {
                            if case .success(let highlights) = highlightsModel.phase {
                                if eveningSummary == nil, let nextShow = highlights.nextShow {
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
                                pinnedClubName: club.name
                            )

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
    static func eveningSummary(
        from highlights: Components.Schemas.ClubHighlights
    ) -> ClubDetailEveningSummary? {
        let shows = highlights.tonightShows.sorted(by: showsBefore)
        guard let earliestShow = shows.first else { return nil }

        var performersByID: [Int: (
            comedian: Components.Schemas.ComedianLineup,
            earliestShow: Components.Schemas.Show
        )] = [:]
        for show in shows {
            for rawComedian in show.lineup ?? [] {
                let comedian = ShowRow.effectiveComedian(rawComedian)
                guard !comedian.name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                    continue
                }
                guard let existing = performersByID[comedian.id] else {
                    performersByID[comedian.id] = (comedian, show)
                    continue
                }
                if performersBefore(comedian, existing.comedian) {
                    performersByID[comedian.id] = (comedian, existing.earliestShow)
                }
            }
        }

        let rankedPerformers = performersByID.values.sorted {
            performersBefore($0.comedian, $1.comedian)
        }
        let visiblePerformers = Array(rankedPerformers.prefix(3)).map { entry in
            ClubDetailMarqueePerformer(
                name: entry.comedian.name,
                localizedStartTime: localizedStartTime(for: entry.earliestShow)
            )
        }
        let performers = visiblePerformers.isEmpty
            ? [ClubDetailMarqueePerformer(
                name: ShowTitlePresentation.title(for: earliestShow),
                localizedStartTime: localizedStartTime(for: earliestShow)
            )]
            : visiblePerformers

        return ClubDetailEveningSummary(performers: performers)
    }

    private static func performersBefore(
        _ lhs: Components.Schemas.ComedianLineup,
        _ rhs: Components.Schemas.ComedianLineup
    ) -> Bool {
        let lhsPopularity = lhs.socialData?.popularity ?? -1
        let rhsPopularity = rhs.socialData?.popularity ?? -1
        if lhsPopularity != rhsPopularity {
            return lhsPopularity > rhsPopularity
        }
        let lhsShowCount = lhs.showCount ?? 0
        let rhsShowCount = rhs.showCount ?? 0
        if lhsShowCount != rhsShowCount {
            return lhsShowCount > rhsShowCount
        }
        return lhs.id < rhs.id
    }

    private static func showsBefore(
        _ lhs: Components.Schemas.Show,
        _ rhs: Components.Schemas.Show
    ) -> Bool {
        if lhs.date != rhs.date {
            return lhs.date < rhs.date
        }
        return lhs.id < rhs.id
    }

    @MainActor
    private static func localizedStartTime(for show: Components.Schemas.Show) -> String {
        ShowFormatting.dateStack(
            show.date,
            timezoneID: show.timezone
        ).time
    }
}

struct ClubDetailMarqueePerformer: Equatable {
    let name: String
    let localizedStartTime: String
}

struct ClubDetailEveningSummary: Equatable {
    let performers: [ClubDetailMarqueePerformer]
}

private struct ClubDetailTonightMarqueeSection: View {
    let summary: ClubDetailEveningSummary

    @Environment(\.appTheme) private var theme

    var body: some View {
        VStack(spacing: 0) {
            Text("Tonight")
                .font(.system(.headline, design: .rounded, weight: .heavy))
                .tracking(2)
                .textCase(.uppercase)
                .foregroundStyle(ClubVenueMarqueeStyle.paper)
                .frame(
                    width: ClubVenueMarqueeStyle.headerWidth,
                    height: ClubVenueMarqueeStyle.headerHeight
                )
                .background {
                    ClubDetailMarqueeHeaderShape()
                        .fill(ClubVenueMarqueeStyle.headerGradient)
                }
                .overlay {
                    ClubDetailMarqueeHeaderShape()
                        .stroke(Color.white.opacity(0.14), lineWidth: 0.75)
                        .padding(2)
                }
                .zIndex(1)

            VStack(spacing: 0) {
                ForEach(Array(summary.performers.enumerated()), id: \.offset) { index, performer in
                    HStack(alignment: .firstTextBaseline, spacing: theme.spacing.md) {
                        Text(performer.name.uppercased())
                            .font(.system(.headline, design: .rounded, weight: .heavy))
                            .tracking(0.6)
                            .lineLimit(1)
                            .minimumScaleFactor(0.72)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        Text(performer.localizedStartTime.uppercased())
                            .font(.system(.footnote, design: .monospaced, weight: .semibold))
                            .tracking(0.4)
                            .foregroundStyle(Color.black.opacity(0.68))
                            .fixedSize(horizontal: true, vertical: false)
                    }
                    .foregroundStyle(Color.black)
                    .padding(.horizontal, theme.spacing.xl)
                    .padding(.vertical, theme.spacing.sm)

                    if index < summary.performers.count - 1 {
                        Divider()
                            .overlay(Color.black.opacity(0.22))
                            .padding(.horizontal, theme.spacing.lg)
                    }
                }
            }
            .padding(.vertical, theme.spacing.md)
            .background {
                RoundedRectangle(
                    cornerRadius: ClubVenueMarqueeStyle.bulbCornerRadius,
                    style: .continuous
                )
                    .stroke(
                        ClubVenueMarqueeStyle.bulbColor,
                        style: ClubVenueMarqueeStyle.bulbStroke
                    )
                    .padding(ClubVenueMarqueeStyle.bulbInset)
                    .shadow(color: ClubVenueMarqueeStyle.bulbColor.opacity(0.35), radius: 3)
            }
        }
        .background {
            ClubDetailMarqueeShellShape()
                .fill(ClubVenueMarqueeStyle.boardGradient)
        }
        .clipShape(ClubDetailMarqueeShellShape())
        .overlay {
            ZStack {
                ClubDetailMarqueeShellShape()
                    .stroke(ClubVenueMarqueeStyle.outline, lineWidth: 1.5)
                ClubDetailMarqueeShellShape()
                    .stroke(Color.white.opacity(0.34), lineWidth: 0.75)
                    .padding(2)
            }
        }
        .shadow(color: Color.black.opacity(0.3), radius: 8, x: 0, y: 5)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier(LaughTrackViewTestID.clubDetailHighlightSection)
    }

}

private struct ClubDetailMarqueeShellShape: Shape {
    func path(in rect: CGRect) -> Path {
        let radius = ClubVenueMarqueeStyle.cornerRadius
        let headerHeight = ClubVenueMarqueeStyle.headerHeight
        let headerWidth = min(ClubVenueMarqueeStyle.headerWidth, rect.width - radius * 4)
        let headerLeading = (rect.width - headerWidth) / 2
        let headerTrailing = headerLeading + headerWidth
        let crownRise: CGFloat = 4

        var path = Path()
        path.move(to: CGPoint(x: headerLeading, y: headerHeight))
        path.addLine(to: CGPoint(x: headerLeading, y: radius + crownRise))
        path.addQuadCurve(
            to: CGPoint(x: headerLeading + radius, y: crownRise),
            control: CGPoint(x: headerLeading, y: crownRise)
        )
        path.addQuadCurve(
            to: CGPoint(x: rect.midX, y: 0),
            control: CGPoint(x: rect.midX - headerWidth * 0.2, y: 0)
        )
        path.addQuadCurve(
            to: CGPoint(x: headerTrailing - radius, y: crownRise),
            control: CGPoint(x: rect.midX + headerWidth * 0.2, y: 0)
        )
        path.addQuadCurve(
            to: CGPoint(x: headerTrailing, y: radius + crownRise),
            control: CGPoint(x: headerTrailing, y: crownRise)
        )
        path.addLine(to: CGPoint(x: headerTrailing, y: headerHeight))
        path.addLine(to: CGPoint(x: rect.maxX - radius, y: headerHeight))
        path.addQuadCurve(
            to: CGPoint(x: rect.maxX, y: headerHeight + radius),
            control: CGPoint(x: rect.maxX, y: headerHeight)
        )
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY - radius))
        path.addQuadCurve(
            to: CGPoint(x: rect.maxX - radius, y: rect.maxY),
            control: CGPoint(x: rect.maxX, y: rect.maxY)
        )
        path.addLine(to: CGPoint(x: radius, y: rect.maxY))
        path.addQuadCurve(
            to: CGPoint(x: 0, y: rect.maxY - radius),
            control: CGPoint(x: 0, y: rect.maxY)
        )
        path.addLine(to: CGPoint(x: 0, y: headerHeight + radius))
        path.addQuadCurve(
            to: CGPoint(x: radius, y: headerHeight),
            control: CGPoint(x: 0, y: headerHeight)
        )
        path.closeSubpath()
        return path
    }
}

private struct ClubDetailMarqueeHeaderShape: Shape {
    func path(in rect: CGRect) -> Path {
        let radius = min(ClubVenueMarqueeStyle.cornerRadius, rect.height / 2)
        let crownRise: CGFloat = 4
        var path = Path()
        path.move(to: CGPoint(x: 0, y: rect.maxY))
        path.addLine(to: CGPoint(x: 0, y: radius + crownRise))
        path.addQuadCurve(
            to: CGPoint(x: radius, y: crownRise),
            control: CGPoint(x: 0, y: crownRise)
        )
        path.addQuadCurve(
            to: CGPoint(x: rect.midX, y: 0),
            control: CGPoint(x: rect.width * 0.3, y: 0)
        )
        path.addQuadCurve(
            to: CGPoint(x: rect.maxX - radius, y: crownRise),
            control: CGPoint(x: rect.width * 0.7, y: 0)
        )
        path.addQuadCurve(
            to: CGPoint(x: rect.maxX, y: radius + crownRise),
            control: CGPoint(x: rect.maxX, y: crownRise)
        )
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))
        path.closeSubpath()
        return path
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
