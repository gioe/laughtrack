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
    @Environment(\.serviceContainer) private var serviceContainer

    @StateObject private var model: ComedianDetailModel
    @State private var feedbackMessage: String?

    fileprivate static let upcomingShowsAnchor = "comedian-upcoming-shows"

    init(comedianID: Int, apiClient: Client) {
        self.comedianID = comedianID
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: ComedianDetailModel(comedianID: comedianID))
    }

    var body: some View {
        Group {
            switch model.phase {
            case .idle, .loading:
                CalendarDetailSkeleton()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.reload(apiClient: apiClient, favorites: favorites) },
                    signIn: { coordinator.push(.profile) }
                )
                .padding()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .success(let content):
                let comedian = content.comedian
                let isFavorite = favorites.value(for: comedian.uuid)
                let stats = ComedianStatsPresentation.stats(for: comedian, runs: content.upcomingRuns)
                ScrollView {
                    ScrollViewReader { proxy in
                        VStack(alignment: .leading, spacing: 0) {
                            DetailHero(
                                title: comedian.name,
                                subtitle: nil,
                                imageURL: comedian.imageUrl,
                                badges: [],
                                actions: comedianHeroActions(socialData: comedian.socialData),
                                openURL: { url in openURL(url) },
                                favoriteState: DetailHeroFavoriteState(
                                    isFavorite: isFavorite,
                                    isPending: favorites.isPending(comedian.uuid),
                                    action: {
                                        await toggleFavorite(name: comedian.name, uuid: comedian.uuid, currentValue: isFavorite)
                                    }
                                )
                            )
                            .ignoresSafeArea(.container, edges: .top)

                            VStack(alignment: .leading, spacing: 20) {
                                if !stats.isEmpty {
                                    ComedianStatsBar(
                                        stats: stats,
                                        hasUpcomingShows: !content.upcomingRuns.isEmpty,
                                        onSeeNextShow: {
                                            withAnimation {
                                                proxy.scrollTo(Self.upcomingShowsAnchor, anchor: .top)
                                            }
                                        }
                                    )
                                }

                                if let relatedContentMessage = content.relatedContentMessage {
                                    InlineStatusMessage(message: relatedContentMessage)
                                }

                                PinnedShowsList(
                                    apiClient: apiClient,
                                    nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self),
                                    pinnedComedianName: comedian.name
                                )
                                .id(Self.upcomingShowsAnchor)

                                if !content.relatedComedians.isEmpty {
                                    LaughTrackCard(tone: .muted, density: .tight) {
                                        VStack(alignment: .leading, spacing: 12) {
                                            LaughTrackSectionHeader(title: "Often on the same bill")

                                            ForEach(ComedianRelatedPresentation.rankedRelatedComedians(
                                                candidates: content.relatedComedians,
                                                runs: content.upcomingRuns,
                                                currentComedianUUID: comedian.uuid
                                            ), id: \.uuid) { relatedComedian in
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
                            .padding(.horizontal, 8)
                            .padding(.vertical, theme.spacing.lg)
                        }
                    }
                }
            }
        }
        .ignoresSafeArea(.container, edges: .top)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .accessibilityIdentifier(LaughTrackViewTestID.comedianDetailScreen)
        .modifier(EntityDetailNavigationChrome(entity: .comedian, title: ""))
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

    private func comedianHeroActions(socialData: Components.Schemas.SocialData) -> [DetailHeroAction] {
        SocialLink.links(from: socialData).map { link in
            DetailHeroAction(
                title: link.label,
                systemImage: socialSymbol(for: link.label),
                url: link.url
            )
        }
    }

    private func socialSymbol(for label: String) -> String {
        switch label {
        case "Instagram": return "camera.fill"
        case "TikTok": return "music.note"
        case "YouTube": return "play.rectangle.fill"
        case "Website": return "safari.fill"
        case "Linktree": return "link"
        default: return "link"
        }
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
}

enum ComedianRelatedPresentation {
    static func rankedRelatedComedians(
        candidates: [Components.Schemas.ComedianLineup],
        runs: [Components.Schemas.UpcomingRun],
        currentComedianUUID: String
    ) -> [Components.Schemas.ComedianLineup] {
        rankedRelatedComedians(
            candidates: candidates,
            shows: runs.flatMap(\.shows),
            currentComedianUUID: currentComedianUUID
        )
    }

    static func rankedRelatedComedians(
        candidates: [Components.Schemas.ComedianLineup],
        shows: [Components.Schemas.Show],
        currentComedianUUID: String
    ) -> [Components.Schemas.ComedianLineup] {
        var counts: [String: Int] = [:]
        var firstSeen: [String: Int] = [:]

        for (showIndex, show) in shows.enumerated() {
            let lineup = show.lineup ?? []
            guard lineup.contains(where: { $0.uuid == currentComedianUUID }) else { continue }

            for (lineupIndex, comedian) in lineup.enumerated() where comedian.uuid != currentComedianUUID {
                counts[comedian.uuid, default: 0] += 1
                firstSeen[comedian.uuid] = min(firstSeen[comedian.uuid] ?? Int.max, showIndex * 1000 + lineupIndex)
            }
        }

        return candidates
            .enumerated()
            .sorted { lhs, rhs in
                let lhsCount = counts[lhs.element.uuid] ?? 0
                let rhsCount = counts[rhs.element.uuid] ?? 0
                if lhsCount != rhsCount { return lhsCount > rhsCount }

                let lhsFirstSeen = firstSeen[lhs.element.uuid] ?? Int.max
                let rhsFirstSeen = firstSeen[rhs.element.uuid] ?? Int.max
                if lhsFirstSeen != rhsFirstSeen { return lhsFirstSeen < rhsFirstSeen }

                return lhs.offset < rhs.offset
            }
            .prefix(5)
            .map(\.element)
    }
}

enum ComedianStatsPresentation {
    enum Stat: Hashable {
        case upcoming(showCount: Int, venueCount: Int)
        case followers(total: Int)
    }

    static func stats(
        for comedian: Components.Schemas.ComedianDetail,
        runs: [Components.Schemas.UpcomingRun]
    ) -> [Stat] {
        var result: [Stat] = []

        let showCount = runs.reduce(0) { $0 + $1.shows.count }
        if showCount > 0 {
            // iOS doesn't carry city/state on Show, so we approximate the web's
            // "in N cities" breadth signal with unique venue counts (one
            // UpcomingRun per club). File a follow-up to surface city directly.
            let venueCount = Set(runs.map(\.clubID)).count
            result.append(.upcoming(showCount: showCount, venueCount: venueCount))
        }

        let social = comedian.socialData
        let total = (social.instagramFollowers ?? 0)
            + (social.tiktokFollowers ?? 0)
            + (social.youtubeFollowers ?? 0)
        if total > 0 {
            result.append(.followers(total: total))
        }

        return result
    }

    static func label(for stat: Stat) -> String {
        switch stat {
        case let .upcoming(showCount, venueCount):
            let showWord = showCount == 1 ? "show" : "shows"
            let base = "\(showCount.formatted()) upcoming \(showWord)"
            guard venueCount > 0 else { return base }
            let venueWord = venueCount == 1 ? "venue" : "venues"
            return "\(base) at \(venueCount.formatted()) \(venueWord)"
        case let .followers(total):
            return "\(compactFollowers(total)) social followers"
        }
    }

    static func systemImage(for stat: Stat) -> String {
        switch stat {
        case .upcoming: return "calendar"
        case .followers: return "person.2.fill"
        }
    }

    private static func compactFollowers(_ value: Int) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.usesGroupingSeparator = false
        formatter.maximumFractionDigits = 1

        switch value {
        case 1_000_000...:
            let scaled = Double(value) / 1_000_000
            return "\(formatter.string(from: NSNumber(value: scaled)) ?? "\(scaled)")M"
        case 1_000...:
            let scaled = Double(value) / 1_000
            return "\(formatter.string(from: NSNumber(value: scaled)) ?? "\(scaled)")K"
        default:
            return value.formatted()
        }
    }
}

struct ComedianStatsBar: View {
    let stats: [ComedianStatsPresentation.Stat]
    let hasUpcomingShows: Bool
    let onSeeNextShow: () -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        LaughTrackCard(density: .tight) {
            VStack(alignment: .leading, spacing: 12) {
                ForEach(stats, id: \.self) { stat in
                    HStack(spacing: 10) {
                        Image(systemName: ComedianStatsPresentation.systemImage(for: stat))
                            .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                            .foregroundStyle(laughTrack.colors.accentStrong)
                            .frame(width: 24)
                        Text(ComedianStatsPresentation.label(for: stat))
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                    }
                }

                if hasUpcomingShows {
                    Button(action: onSeeNextShow) {
                        HStack(spacing: 8) {
                            Image(systemName: "calendar")
                                .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                            Text("See next show")
                                .font(laughTrack.typography.body.weight(.semibold))
                            Spacer(minLength: 0)
                            Image(systemName: "chevron.right")
                                .font(.system(size: 13, weight: .semibold))
                                .foregroundStyle(laughTrack.colors.textInverse.opacity(0.7))
                        }
                        .foregroundStyle(laughTrack.colors.textInverse)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 12)
                        .frame(maxWidth: .infinity)
                        .background(laughTrack.colors.accentStrong)
                        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
                    }
                    .buttonStyle(.plain)
                    .accessibilityHint("Scrolls to the upcoming shows list")
                }
            }
        }
    }
}
