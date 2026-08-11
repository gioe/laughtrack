import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct HomeDiscoverPlannedRail: View {
    let section: HomeDiscoverRailSection
    let searchNavigationBridge: SearchNavigationBridge
    let nearbyPreference: NearbyPreference?

    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController

    private var analytics: (any AnalyticsManagerProtocol)? {
        serviceContainer.resolveOptional(AnalyticsManagerProtocol.self)
    }

    var body: some View {
        switch section.content {
        case .showsTonight(let shows):
            HomeDiscoverRailCard(
                variant: .spotlight,
                eyebrow: nil,
                title: nil,
                subtitle: nil,
                accessibilityIdentifier: LaughTrackViewTestID.homeShowsTonightRail,
                actionTitle: "See all",
                actionAccessibilityIdentifier: HomeShowRailKind.showsTonight.seeMoreAccessibilityIdentifier,
                action: { openSeeAll(railKind: .showsTonight) }
            ) {
                HomeFeaturedShowsCarousel(
                    headline: "Tonight!",
                    items: HomeFeaturedShowCarouselItem.tonightItems(shows),
                    onSelect: trackSelection
                )
            }

        case .followedComedianShows(let shows):
            HomeDiscoverRailCard(
                variant: .spotlight,
                eyebrow: nil,
                title: nil,
                subtitle: nil,
                accessibilityIdentifier: "laughtrack.home.followed-comedian-shows-rail"
            ) {
                HomeFeaturedShowsCarousel(
                    headline: "Because you follow them",
                    items: shows.prefix(HomeDiscoverRailPlanPresentation.itemLimit).map { show in
                        HomeFeaturedShowCarouselItem(
                            show: show,
                            preferredHeadlinerID: HomeDiscoverRailPlanPresentation.preferredFavoriteHeadlinerID(
                                show: show
                            ),
                            accessibilityIdentifier: "laughtrack.home.followed-comedian-shows-show-\(show.id)",
                            accessibilityLabel: ShowTitlePresentation.title(for: show),
                            timestampLabel: ShowFormatting.featuredDateTime(
                                show.date,
                                timezoneID: show.timezone
                            )
                        )
                    },
                    onSelect: trackSelection
                )
            }

        case .trendingThisWeek(let shows):
            showListRail(
                shows: shows,
                eyebrow: "Coming Up",
                title: "Best shows this week",
                accessibilityIdentifier: "laughtrack.home.this-week-rail",
                seeMoreRailKind: .thisWeek
            )

        case .trendingComedians(let comedians):
            HomeDiscoverRailCard(
                variant: .posterGrid,
                eyebrow: "Drawing Crowds",
                title: "Popular local comedians",
                subtitle: nil,
                accessibilityIdentifier: LaughTrackViewTestID.homeTrendingComediansRail,
                actionTitle: "See all",
                action: {
                    trackSelection()
                    searchNavigationBridge.openSearch(.discoverEntity(.comedians))
                }
            ) {
                LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
                    ForEach(comedians, id: \.uuid) { comedian in
                        Button {
                            trackSelection()
                            coordinator.open(.comedian(comedian.id))
                        } label: {
                            HomeTrendingComedianCard(comedian: comedian)
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier(LaughTrackViewTestID.homeTrendingComedianButton(comedian.id))
                    }
                }
            }

        case .popularClubs(let clubs):
            HomeDiscoverRailCard(
                variant: .posterGrid,
                eyebrow: "Hot Rooms",
                title: "Popular local clubs",
                subtitle: nil,
                accessibilityIdentifier: LaughTrackViewTestID.homePopularClubsRail,
                actionTitle: "See all",
                action: {
                    trackSelection()
                    searchNavigationBridge.openSearch(
                        .discoverEntity(.clubs, nearbyPreference: nearbyPreference)
                    )
                }
            ) {
                LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
                    ForEach(clubs, id: \.id) { club in
                        Button {
                            trackSelection()
                            coordinator.open(.club(club.id))
                        } label: {
                            HomePopularClubCard(club: club)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

        case .podcastEpisodes(let episodes):
            HomeDiscoverRailCard(
                variant: .listeningRoom,
                eyebrow: "Funny listening",
                title: "Episodes for you",
                subtitle: nil,
                accessibilityIdentifier: LaughTrackViewTestID.homeTrendingPodcastsRail
            ) {
                VStack(spacing: theme.spacing.sm) {
                    ForEach(episodes, id: \.id) { episode in
                        let item = HomePodcastEpisodeDiscoveryPresentation.item(from: episode)
                        PodcastEpisodeDiscoveryRow(
                            item: item,
                            onSelect: {
                                trackSelection()
                                coordinator.push(HomePodcastEpisodeDiscoveryPresentation.route(for: item))
                            },
                            onPlay: item.playbackItem.map { playbackItem in
                                {
                                    trackSelection()
                                    podcastPlayer.start(playbackItem)
                                }
                            }
                        )
                    }
                }
            }

        case .nearbyShows(let shows):
            showListRail(
                shows: shows,
                eyebrow: "Near You",
                title: "More shows nearby",
                accessibilityIdentifier: "laughtrack.home.nearby-shows-rail"
            )

        case .dynamicShows(let label, let items):
            if HomeDiscoverRailPlanPresentation.usesTodayStyleShowCarousel(railKey: section.id) {
                HomeDiscoverRailCard(
                    variant: .spotlight,
                    eyebrow: nil,
                    title: nil,
                    subtitle: nil,
                    accessibilityIdentifier: "laughtrack.home.dynamic-\(section.id)-rail"
                ) {
                    HomeFeaturedShowsCarousel(
                        headline: label,
                        items: items.map { item in
                            HomeFeaturedShowCarouselItem(
                                show: item.show,
                                preferredHeadlinerID: HomeDiscoverRailPlanPresentation.preferredHeadlinerID(
                                    railKey: section.id,
                                    item: item
                                ),
                                accessibilityIdentifier: "laughtrack.home.dynamic-\(section.id)-show-\(item.show.id)",
                                accessibilityLabel: "\(ShowTitlePresentation.title(for: item.show)). \(item.reason.label)",
                                timestampLabel: ShowFormatting.featuredDateTime(
                                    item.show.date,
                                    timezoneID: item.show.timezone
                                )
                            )
                        },
                        onSelect: trackSelection
                    )
                }
            } else {
                HomeDiscoverRailCard(
                    variant: .scheduleBoard,
                    eyebrow: "Picked for you",
                    title: label,
                    subtitle: nil,
                    accessibilityIdentifier: "laughtrack.home.dynamic-\(section.id)-rail"
                ) {
                    VStack(spacing: theme.spacing.sm) {
                        ForEach(items, id: \.id) { item in
                            Button {
                                trackSelection()
                                coordinator.open(.show(item.show.id))
                            } label: {
                                ShowRow(
                                    show: item.show,
                                    presentation: .compactTicket,
                                    preferredHeadlinerID: HomeDiscoverRailPlanPresentation.preferredHeadlinerID(
                                        railKey: section.id,
                                        item: item
                                    )
                                )
                            }
                            .buttonStyle(.plain)
                            .accessibilityElement(children: .combine)
                            .accessibilityLabel(
                                "\(ShowTitlePresentation.title(for: item.show)). \(item.reason.label)"
                            )
                        }
                    }
                }
            }
        }
    }

    private var gridColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: theme.spacing.sm),
            GridItem(.flexible(), spacing: theme.spacing.sm),
        ]
    }

    private func showListRail(
        shows: [Components.Schemas.Show],
        eyebrow: String?,
        title: String,
        accessibilityIdentifier: String,
        seeMoreRailKind: HomeShowRailKind? = nil
    ) -> some View {
        HomeDiscoverRailCard(
            variant: .scheduleBoard,
            eyebrow: eyebrow,
            title: title,
            subtitle: nil,
            accessibilityIdentifier: accessibilityIdentifier,
            actionTitle: seeMoreRailKind == nil ? nil : "See all",
            actionAccessibilityIdentifier: seeMoreRailKind?.seeMoreAccessibilityIdentifier,
            action: seeMoreRailKind.map { railKind in
                { openSeeAll(railKind: railKind) }
            }
        ) {
            VStack(spacing: theme.spacing.sm) {
                ForEach(shows, id: \.id) { show in
                    Button {
                        trackSelection()
                        coordinator.open(.show(show.id))
                    } label: {
                        ShowRow(show: show, presentation: .compactTicket)
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier(LaughTrackViewTestID.homeShowsTonightButton(show.id))
                }
            }
        }
    }

    private func openSeeAll(railKind: HomeShowRailKind) {
        trackSelection()
        searchNavigationBridge.openSearch(
            HomeShowsTonightModel.seeMoreSearchSeed(
                railKind: railKind,
                nearbyPreference: nearbyPreference
            )
        )
    }

    private func trackSelection() {
        analytics?.track(
            DiscoverAnalyticsEvents.railSelected,
            parameters: DiscoverAnalyticsEvents.parameters(
                railKey: section.id,
                policyVersion: section.policyVersion,
                rank: section.rank
            )
        )
    }
}
