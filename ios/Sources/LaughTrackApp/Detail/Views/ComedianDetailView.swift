import SwiftUI
import AVFoundation
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
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL
    @Environment(\.serviceContainer) private var serviceContainer

    @StateObject private var model: ComedianDetailModel
    @State private var feedbackMessage: String?
    @State private var activeTab: ComedianDetailTab = .upcoming
    @State private var activatedTabs: Set<ComedianDetailTab> = [.upcoming]

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
                                            activate(.upcoming)
                                            withAnimation {
                                                proxy.scrollTo(Self.upcomingShowsAnchor, anchor: .top)
                                            }
                                        }
                                    )
                                }

                                if let relatedContentMessage = content.relatedContentMessage {
                                    InlineStatusMessage(message: relatedContentMessage)
                                }

                                Picker("Section", selection: tabSelectionBinding) {
                                    ForEach(ComedianDetailTab.allCases) { tab in
                                        Text(tab.title).tag(tab)
                                    }
                                }
                                .pickerStyle(.segmented)
                                .accessibilityIdentifier(LaughTrackViewTestID.comedianDetailTabPicker)

                                ZStack(alignment: .top) {
                                    PinnedShowsList(
                                        apiClient: apiClient,
                                        nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self),
                                        pinnedComedianName: comedian.name
                                    )
                                    .id(Self.upcomingShowsAnchor)
                                    .modifier(ComedianDetailTabPanelVisibility(isActive: activeTab == .upcoming))

                                    if activatedTabs.contains(.past) {
                                        ComedianPastShowsPanel(
                                            model: model,
                                            apiClient: apiClient,
                                            comedianName: comedian.name,
                                            onOpenShow: { showID in coordinator.open(.show(showID)) },
                                            onSignIn: { coordinator.push(.profile) }
                                        )
                                        .modifier(ComedianDetailTabPanelVisibility(isActive: activeTab == .past))
                                    }

                                    if activatedTabs.contains(.related) {
                                        ComedianRelatedPanel(
                                            relatedComedians: content.relatedComedians,
                                            upcomingRuns: content.upcomingRuns,
                                            currentComedianUUID: comedian.uuid,
                                            apiClient: apiClient,
                                            feedbackMessage: $feedbackMessage,
                                            onOpenComedian: { comedianID in coordinator.open(.comedian(comedianID)) }
                                        )
                                        .modifier(ComedianDetailTabPanelVisibility(isActive: activeTab == .related))
                                    }

                                    if activatedTabs.contains(.podcasts) {
                                        ComedianPodcastPanel(
                                            appearances: comedian.podcastAppearances,
                                            podcastPlayer: podcastPlayer
                                        )
                                        .modifier(ComedianDetailTabPanelVisibility(isActive: activeTab == .podcasts))
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

    private var tabSelectionBinding: Binding<ComedianDetailTab> {
        Binding(
            get: { activeTab },
            set: { activate($0) }
        )
    }

    private func activate(_ tab: ComedianDetailTab) {
        activeTab = tab
        activatedTabs.insert(tab)
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
        case upcoming(showCount: Int, cityCount: Int)
        case followers(total: Int)
    }

    static func stats(
        for comedian: Components.Schemas.ComedianDetail,
        runs: [Components.Schemas.UpcomingRun]
    ) -> [Stat] {
        var result: [Stat] = []

        let showCount = runs.reduce(0) { $0 + $1.shows.count }
        if showCount > 0 {
            let cityCount = uniqueCityCount(in: runs)
            result.append(.upcoming(showCount: showCount, cityCount: cityCount))
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
        case let .upcoming(showCount, cityCount):
            let showWord = showCount == 1 ? "show" : "shows"
            let base = "\(showCount.formatted()) upcoming \(showWord)"
            guard cityCount > 0 else { return base }
            let cityWord = cityCount == 1 ? "city" : "cities"
            return "\(base) in \(cityCount.formatted()) \(cityWord)"
        case let .followers(total):
            return "\(compactFollowers(total)) social followers"
        }
    }

    private static func uniqueCityCount(in runs: [Components.Schemas.UpcomingRun]) -> Int {
        var cities = Set<String>()
        for show in runs.flatMap(\.shows) {
            let city = show.clubCity?.trimmingCharacters(in: .whitespacesAndNewlines)
            guard let city, !city.isEmpty else { continue }
            let state = show.clubState?.trimmingCharacters(in: .whitespacesAndNewlines)
            if let state, !state.isEmpty {
                cities.insert("\(city), \(state)")
            } else {
                cities.insert(city)
            }
        }
        return cities.count
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

/// Keeps an activated tab panel in the view hierarchy so its `@StateObject`s
/// (notably `PinnedShowsList`'s `ShowsListModel`) survive tab switches, mirroring
/// the web `activatedTabs` pattern. Inactive panels collapse to zero layout space
/// so the ScrollView sizes only to the active tab.
private struct ComedianDetailTabPanelVisibility: ViewModifier {
    let isActive: Bool

    func body(content: Content) -> some View {
        content
            .frame(maxHeight: isActive ? nil : 0, alignment: .top)
            .clipped()
            .opacity(isActive ? 1 : 0)
            .allowsHitTesting(isActive)
            .accessibilityHidden(!isActive)
    }
}

enum ComedianDetailTab: String, CaseIterable, Identifiable {
    case upcoming
    case past
    case related
    case podcasts

    var id: String { rawValue }

    var title: String {
        switch self {
        case .upcoming: return "Upcoming"
        case .past: return "Past"
        case .related: return "Related"
        case .podcasts: return "Podcasts"
        }
    }
}

struct ComedianPastShowsPanel: View {
    @ObservedObject var model: ComedianDetailModel
    let apiClient: Client
    let comedianName: String
    let onOpenShow: (Int) -> Void
    let onSignIn: () -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        LaughTrackCard(density: .compact) {
            VStack(alignment: .leading, spacing: theme.spacing.md) {
                LaughTrackSectionHeader(title: "Past Shows")

                switch model.pastShowsPhase {
                case .idle, .loading:
                    ShowsListSkeleton()
                case .failure(let failure):
                    FailureCard(
                        failure: failure,
                        retry: {
                            await model.reloadPastShows(
                                apiClient: apiClient,
                                comedianName: comedianName
                            )
                        },
                        signIn: onSignIn
                    )
                case .success(let page):
                    if page.shows.isEmpty {
                        EmptyCard(
                            title: "No past shows yet",
                            message: "LaughTrack hasn't recorded a show for \(comedianName) yet."
                        )
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            SearchResultsSummary(count: page.shows.count, total: page.total)

                            ForEach(page.shows, id: \.id) { show in
                                Button {
                                    onOpenShow(show.id)
                                } label: {
                                    ShowRow(show: show)
                                }
                                .buttonStyle(.plain)
                            }

                            if let paginationFailure = model.pastShowsPaginationFailure {
                                InlineStatusMessage(message: paginationFailure.message)
                            }

                            if page.canLoadMore {
                                LoadMoreButton(
                                    title: "Load more past shows",
                                    isLoading: model.isLoadingMorePastShows
                                ) {
                                    await model.loadMorePastShows(
                                        apiClient: apiClient,
                                        comedianName: comedianName
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
        .task {
            await model.loadPastShowsIfNeeded(
                apiClient: apiClient,
                comedianName: comedianName
            )
        }
    }
}

struct ComedianRelatedPanel: View {
    let relatedComedians: [Components.Schemas.ComedianLineup]
    let upcomingRuns: [Components.Schemas.UpcomingRun]
    let currentComedianUUID: String
    let apiClient: Client
    @Binding var feedbackMessage: String?
    let onOpenComedian: (Int) -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        let ranked = ComedianRelatedPresentation.rankedRelatedComedians(
            candidates: relatedComedians,
            runs: upcomingRuns,
            currentComedianUUID: currentComedianUUID
        )

        LaughTrackCard(tone: .muted, density: .tight) {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(title: "Often on the same bill")

                if ranked.isEmpty {
                    EmptyCard(
                        title: "No related comedians yet",
                        message: "LaughTrack hasn't matched this comedian with shared-bill comedians yet."
                    )
                } else {
                    ForEach(ranked, id: \.uuid) { relatedComedian in
                        ComedianLineupRow(
                            comedian: relatedComedian,
                            apiClient: apiClient,
                            feedbackMessage: $feedbackMessage,
                            openDetail: { onOpenComedian(relatedComedian.id) }
                        )
                    }
                }
            }
        }
    }
}

struct PodcastPlaybackItem: Identifiable, Equatable, Hashable {
    let id: Int
    let episodeTitle: String
    let podcastName: String
    let podcastImageURL: String?
    let displayRole: String
    let audioURL: URL?
    let episodeURL: URL?
    let failedAudioURL: URL?

    var requiresExternalFallback: Bool {
        audioURL == nil || failedAudioURL != nil
    }

    func markingAudioFailed() -> PodcastPlaybackItem {
        .init(
            id: id,
            episodeTitle: episodeTitle,
            podcastName: podcastName,
            podcastImageURL: podcastImageURL,
            displayRole: displayRole,
            audioURL: nil,
            episodeURL: episodeURL,
            failedAudioURL: audioURL ?? failedAudioURL
        )
    }
}

struct ComedianPodcastPlaybackSegments: Equatable {
    let appearances: [PodcastPlaybackItem]
    let comedianPodcast: [PodcastPlaybackItem]
}

enum ComedianPodcastPresentation {
    static func playbackItem(for appearance: Components.Schemas.PodcastAppearance) -> PodcastPlaybackItem? {
        let audioURL = URL.normalizedExternalURL(appearance.episode.audioUrl)
        let episodeURL = URL.normalizedExternalURL(appearance.episode.episodeUrl)
        guard audioURL != nil || episodeURL != nil else { return nil }

        return .init(
            id: appearance.id,
            episodeTitle: appearance.episode.title,
            podcastName: appearance.podcast.title,
            podcastImageURL: appearance.podcast.imageUrl,
            displayRole: displayRole(for: appearance.role),
            audioURL: audioURL,
            episodeURL: episodeURL,
            failedAudioURL: nil
        )
    }

    static func playbackItems(for appearances: [Components.Schemas.PodcastAppearance]) -> [PodcastPlaybackItem] {
        appearances.compactMap(playbackItem(for:))
    }

    static func segmentedPlaybackItems(for appearances: [Components.Schemas.PodcastAppearance]) -> ComedianPodcastPlaybackSegments {
        var guestItems: [PodcastPlaybackItem] = []
        var hostItems: [PodcastPlaybackItem] = []

        for appearance in appearances {
            guard let item = playbackItem(for: appearance) else { continue }

            if isHostedRole(appearance.role) {
                hostItems.append(item)
            } else {
                guestItems.append(item)
            }
        }

        return .init(appearances: guestItems, comedianPodcast: hostItems)
    }

    private static func displayRole(for role: String) -> String {
        switch role.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
        case "host":
            return "Host"
        case "cohost":
            return "Cohost"
        default:
            return "Guest"
        }
    }

    private static func isHostedRole(_ role: String) -> Bool {
        switch role.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
        case "host", "cohost":
            return true
        default:
            return false
        }
    }
}

protocol PodcastAudioEngine: AnyObject {
    func load(url: URL, onFailure: @escaping @MainActor () -> Void)
    func play()
    func pause()
    func stop()
}

final class AVPodcastAudioEngine: PodcastAudioEngine {
    private var player: AVPlayer?
    private var statusObservation: NSKeyValueObservation?

    func load(url: URL, onFailure: @escaping @MainActor () -> Void) {
        let item = AVPlayerItem(url: url)
        statusObservation = item.observe(\.status, options: [.new]) { item, _ in
            guard item.status == .failed else { return }
            Task { @MainActor in onFailure() }
        }
        player = AVPlayer(playerItem: item)
    }

    func play() {
        player?.play()
    }

    func pause() {
        player?.pause()
    }

    func stop() {
        player?.pause()
        player = nil
        statusObservation = nil
    }
}

@MainActor
final class PodcastPlaybackController: ObservableObject {
    @Published private(set) var currentItem: PodcastPlaybackItem?
    @Published private(set) var isPlaying = false

    private let audioEngine: PodcastAudioEngine

    init(audioEngine: PodcastAudioEngine = AVPodcastAudioEngine()) {
        self.audioEngine = audioEngine
    }

    func start(_ item: PodcastPlaybackItem) {
        currentItem = item
        guard let audioURL = item.audioURL else {
            audioEngine.stop()
            isPlaying = false
            return
        }

        audioEngine.load(url: audioURL) { [weak self] in
            self?.markCurrentItemFailed()
        }
        audioEngine.play()
        isPlaying = true
    }

    func pause() {
        audioEngine.pause()
        isPlaying = false
    }

    func resume() {
        guard let item = currentItem, item.audioURL != nil else { return }
        audioEngine.play()
        isPlaying = true
    }

    func dismiss() {
        audioEngine.stop()
        currentItem = nil
        isPlaying = false
    }

    func markCurrentItemFailed() {
        guard let currentItem else { return }
        audioEngine.stop()
        self.currentItem = currentItem.markingAudioFailed()
        isPlaying = false
    }
}

struct ComedianPodcastPanel: View {
    let appearances: [Components.Schemas.PodcastAppearance]
    @ObservedObject var podcastPlayer: PodcastPlaybackController

    @Environment(\.appTheme) private var theme

    var body: some View {
        let segments = ComedianPodcastPresentation.segmentedPlaybackItems(for: appearances)

        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            podcastSubsection(
                title: "Podcast Appearances",
                emptyTitle: "No playable podcast appearances yet",
                emptyMessage: "LaughTrack has not matched this comedian with playable guest podcast appearances yet.",
                items: segments.appearances
            )

            podcastSubsection(
                title: "Comedian's Podcast",
                emptyTitle: "No hosted podcast episodes yet",
                emptyMessage: "LaughTrack has not matched this comedian with playable host or cohost podcast episodes yet.",
                items: segments.comedianPodcast
            )
        }
    }

    @ViewBuilder
    private func podcastSubsection(
        title: String,
        emptyTitle: String,
        emptyMessage: String,
        items: [PodcastPlaybackItem]
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            LaughTrackSectionHeader(title: title)

            if items.isEmpty {
                EmptyCard(title: emptyTitle, message: emptyMessage)
            } else {
                ForEach(items) { item in
                    PodcastAppearanceRow(
                        item: item,
                        isCurrent: podcastPlayer.currentItem?.id == item.id
                    ) {
                        podcastPlayer.start(item)
                    }
                }
            }
        }
    }
}

private struct PodcastAppearanceRow: View {
    let item: PodcastPlaybackItem
    let isCurrent: Bool
    let onSelect: () -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button(action: onSelect) {
            HStack(alignment: .top, spacing: theme.spacing.md) {
                artwork

                VStack(alignment: .leading, spacing: 4) {
                    Text(item.episodeTitle)
                        .font(laughTrack.typography.body.weight(.semibold))
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .lineLimit(2)
                    HStack(spacing: 8) {
                        Text(item.podcastName)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .lineLimit(1)

                        PodcastAppearanceRoleBadge(title: item.displayRole)
                    }
                }

                Spacer(minLength: 0)

                if isCurrent {
                    Image(systemName: "waveform")
                        .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.accent)
                        .accessibilityLabel("Now playing")
                }
            }
            .frame(maxWidth: .infinity, minHeight: 86, alignment: .leading)
            .padding(.horizontal, laughTrack.browseDensity.compactCardPadding)
            .padding(.vertical, laughTrack.browseDensity.compactCardPadding)
            .background(laughTrack.colors.surfaceElevated)
            .overlay(
                RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                    .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
            .shadowStyle(laughTrack.shadows.card)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(item.episodeTitle), \(item.podcastName), \(item.displayRole)")
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens
        let rawImageURL = item.podcastImageURL?.trimmingCharacters(in: .whitespacesAndNewlines)

        if let url = URL.normalizedExternalURL(rawImageURL) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                artworkBackground
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                fallbackArtwork
            }
            .frame(width: 56, height: 56)
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        } else {
            fallbackArtwork
        }
    }

    private var artworkBackground: some View {
        RoundedRectangle(cornerRadius: 10, style: .continuous)
            .fill(theme.laughTrackTokens.colors.surfaceMuted)
            .frame(width: 56, height: 56)
    }

    private var fallbackArtwork: some View {
        artworkBackground
            .overlay {
                Image(systemName: "music.mic")
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(theme.laughTrackTokens.colors.accentStrong)
            }
    }
}

private struct PodcastAppearanceRoleBadge: View {
    let title: String

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Text(title)
            .font(laughTrack.typography.metadata.weight(.semibold))
            .foregroundStyle(laughTrack.colors.accentStrong)
            .lineLimit(1)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(laughTrack.colors.accentMuted.opacity(0.24))
            .overlay(
                Capsule(style: .continuous)
                    .stroke(laughTrack.colors.accentMuted.opacity(0.45), lineWidth: 1)
            )
            .clipShape(Capsule(style: .continuous))
    }
}

#Preview("Podcast row beside show row") {
    ScrollView {
        VStack(alignment: .leading, spacing: 12) {
            PodcastAppearanceRow(
                item: PodcastPlaybackItem(
                    id: 1,
                    episodeTitle: "Comedy Cellar Stories",
                    podcastName: "The Laugh Track Pod",
                    podcastImageURL: "https://images.unsplash.com/photo-1478737270239-2f02b77fc618?auto=format&fit=crop&w=240&q=80",
                    displayRole: "Guest",
                    audioURL: URL(string: "https://cdn.example.com/episodes/cellar.mp3"),
                    episodeURL: URL(string: "https://podcasts.example.com/cellar"),
                    failedAudioURL: nil
                ),
                isCurrent: true,
                onSelect: {}
            )

            ShowRow(
                show: Components.Schemas.Show(
                    id: 301,
                    clubID: 201,
                    clubName: "Comedy Cellar",
                    date: Date().addingTimeInterval(60 * 60 * 24),
                    tickets: [.init(price: 30, purchaseUrl: "https://laughtrack.app/demo/tickets/301", soldOut: false, _type: "General admission")],
                    name: "Mark Normand and Friends",
                    socialData: nil,
                    lineup: [
                        .init(
                            name: "Mark Normand",
                            imageUrl: "https://images.unsplash.com/photo-1516280440614-37939bbacd81?auto=format&fit=crop&w=240&q=80",
                            uuid: "demo-comedian-101",
                            id: 101,
                            userId: nil,
                            socialData: nil,
                            isFavorite: false,
                            showCount: 12
                        )
                    ],
                    description: "A demo lineup used for preview comparison.",
                    address: "117 MacDougal St, New York, NY",
                    room: "Main Room",
                    imageUrl: "https://images.unsplash.com/photo-1503095396549-807759245b35?auto=format&fit=crop&w=1200&q=80",
                    soldOut: false,
                    distanceMiles: 2.1
                )
            )
        }
        .padding()
    }
    .background(LaughTrackTheme().laughTrackTokens.colors.canvas)
    .environment(\.appTheme, LaughTrackTheme())
}
