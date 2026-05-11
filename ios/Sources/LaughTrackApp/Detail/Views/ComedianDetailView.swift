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
    @State private var safariURL: URL?
    @State private var selectedDates: Set<Date> = []

    private var nearbyLocationController: NearbyLocationController {
        serviceContainer.resolve(NearbyLocationController.self)
    }

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
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                    DetailHero(
                        title: comedian.name,
                        subtitle: nil,
                        imageURL: comedian.imageUrl,
                        badges: [],
                        actions: comedianHeroActions(socialData: comedian.socialData),
                        openURL: { url in
                            ExternalLinkRouter.route(url, presentedURL: $safariURL, openURL: openURL)
                        },
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
                        LaughTrackCard(density: .tight) {
                            VStack(alignment: .leading, spacing: 12) {
                                LaughTrackSectionHeader(
                                    title: "Upcoming shows",
                                    subtitle: upcomingShowsCountSubtitle(
                                        showing: showingShowsCount(in: content.upcomingShows),
                                        total: content.upcomingShowsTotal
                                    )
                                )

                                if let relatedContentMessage = content.relatedContentMessage {
                                    InlineStatusMessage(message: relatedContentMessage)
                                }

                                ShowsCalendarSection(
                                    shows: content.upcomingShows,
                                    onSelectShow: { showID in coordinator.open(.show(showID)) },
                                    selectedDates: $selectedDates,
                                    jumpToDate: Binding(
                                        get: { model.fromDate },
                                        set: { newDate in
                                            model.fromDate = newDate
                                            Task { await model.refreshUpcomingShows(apiClient: apiClient, favorites: favorites) }
                                        }
                                    ),
                                    isRefreshing: model.isRefetchingShows,
                                    isNearMe: nearbyMatcher()
                                )
                            }
                        }

                        if !content.relatedComedians.isEmpty {
                            LaughTrackCard(tone: .muted, density: .tight) {
                                VStack(alignment: .leading, spacing: 12) {
                                    LaughTrackSectionHeader(title: "Often on the same bill")

                                    ForEach(Array(content.relatedComedians.prefix(5)), id: \.uuid) { relatedComedian in
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
                .safariSheet(url: $safariURL)
            }
        }
        .ignoresSafeArea(.container, edges: .top)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .accessibilityIdentifier(LaughTrackViewTestID.comedianDetailScreen)
        .modifier(EntityDetailNavigationChrome(entity: .comedian))
        .task {
            model.nearbyZipCode = nearbyLocationController.preference?.zipCode
            model.nearbyDistanceMiles = nearbyLocationController.preference?.distanceMiles
            await model.loadIfNeeded(apiClient: apiClient, favorites: favorites)
        }
        .onReceive(nearbyLocationController.$preference) { preference in
            let newZip = preference?.zipCode
            let newDistance = preference?.distanceMiles
            guard newZip != model.nearbyZipCode || newDistance != model.nearbyDistanceMiles else { return }
            model.nearbyZipCode = newZip
            model.nearbyDistanceMiles = newDistance
            if case .success = model.phase {
                Task { await model.refreshUpcomingShows(apiClient: apiClient, favorites: favorites) }
            }
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

    private func upcomingShowsCountSubtitle(showing: Int, total: Int) -> String? {
        guard total > 0 else { return nil }
        let totalLabel = total == 1 ? "1 total" : "\(total) total"
        return "\(showing) showing · \(totalLabel)"
    }

    private func showingShowsCount(in shows: [Components.Schemas.Show]) -> Int {
        let calendar = Calendar.current
        let weekStart = calendar.startOfDay(for: model.fromDate)
        let weekDates: Set<Date> = Set((0..<7).compactMap { offset in
            calendar.date(byAdding: .day, value: offset, to: weekStart).map { calendar.startOfDay(for: $0) }
        })
        let inWeek = shows.filter { weekDates.contains(calendar.startOfDay(for: $0.date)) }

        guard !selectedDates.isEmpty else { return inWeek.count }
        let selected = Set(selectedDates.map { calendar.startOfDay(for: $0) })
        return inWeek.filter { selected.contains(calendar.startOfDay(for: $0.date)) }.count
    }

    private func nearbyMatcher() -> ((Components.Schemas.Show) -> Bool)? {
        guard let preference = nearbyLocationController.preference else { return nil }
        let radius = Double(preference.distanceMiles)
        return { show in
            guard let distance = show.distanceMiles else { return false }
            return distance <= radius
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
