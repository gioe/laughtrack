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
    @State private var expandedRunKeys: Set<String> = []
    @State private var searchText: String = ""
    @State private var locationFilterText: String = ""
    @State private var useDateFilter: Bool = false
    @State private var dateFilter: Date = Calendar.current.startOfDay(for: Date())

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
                    retry: { await model.reload(apiClient: apiClient, favorites: favorites, runFilters: activeRunFilters) },
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
                        LaughTrackCard(density: .tight) {
                            VStack(alignment: .leading, spacing: 12) {
                                LaughTrackSectionHeader(title: "Upcoming shows")

                                if let relatedContentMessage = content.relatedContentMessage {
                                    InlineStatusMessage(message: relatedContentMessage)
                                }

                                UpcomingShowsFilterPanel(
                                    searchText: $searchText,
                                    locationFilterText: $locationFilterText,
                                    useDateFilter: $useDateFilter,
                                    dateFilter: $dateFilter,
                                    showsByDate: Self.showsByDate(content.upcomingRuns)
                                )

                                if content.upcomingRuns.isEmpty {
                                    EmptyCard(message: ComedianDetailPresentation.emptyUpcomingShowsMessage(filters: activeRunFilters))
                                } else {
                                    VStack(spacing: theme.spacing.sm) {
                                        ForEach(content.upcomingRuns, id: \.id) { run in
                                            ComedianClubRunDisclosure(
                                                run: run,
                                                isExpanded: Binding(
                                                    get: { expandedRunKeys.contains(run.id) },
                                                    set: { newValue in
                                                        if newValue { expandedRunKeys.insert(run.id) }
                                                        else { expandedRunKeys.remove(run.id) }
                                                    }
                                                ),
                                                nearbyRadiusMiles: nearbyRadiusMiles,
                                                openShow: { showID in coordinator.open(.show(showID)) }
                                            )
                                        }
                                    }
                                }
                            }
                        }

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
        .ignoresSafeArea(.container, edges: .top)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .accessibilityIdentifier(LaughTrackViewTestID.comedianDetailScreen)
        .modifier(EntityDetailNavigationChrome(entity: .comedian))
        .task(id: activeRunFilters) {
            await model.reload(apiClient: apiClient, favorites: favorites, runFilters: activeRunFilters)
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

    static func showsByDate(_ runs: [Components.Schemas.UpcomingRun]) -> [Date: Int] {
        let calendar = Calendar.current
        var counts: [Date: Int] = [:]
        for run in runs {
            for show in run.shows {
                let day = calendar.startOfDay(for: show.date)
                counts[day, default: 0] += 1
            }
        }
        return counts
    }

    private var activeRunFilters: ComedianRunFilters {
        ComedianRunFilters(
            club: normalizedFilter(searchText),
            location: normalizedFilter(locationFilterText),
            date: useDateFilter ? ShowFormatting.apiDate(dateFilter) : nil
        )
    }

    private var nearbyRadiusMiles: Double? {
        serviceContainer.resolve(NearbyLocationController.self).preference.map { Double($0.distanceMiles) }
    }

    private func normalizedFilter(_ value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
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

enum ComedianDetailPresentation {
    static func emptyUpcomingShowsMessage(filters: ComedianRunFilters) -> String {
        filters == .empty
            ? "No upcoming shows are available for this comedian right now."
            : "No shows match these filters. Try clearing one."
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

extension Components.Schemas.UpcomingRun {
    var id: String {
        guard let firstShowID = shows.first?.id else { return "\(clubID)-empty" }
        return "\(clubID)-\(firstShowID)"
    }

    var dateRangeSummary: String {
        guard let first = shows.first, let last = shows.last else { return "" }
        let timezone = first.timezone.flatMap { TimeZone(identifier: $0) }

        if shows.count == 1 {
            let formatter = DateFormatter()
            formatter.dateFormat = "MMM d 'at' h:mm a"
            if let timezone { formatter.timeZone = timezone }
            return formatter.string(from: first.date)
        }

        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d"
        if let timezone { formatter.timeZone = timezone }
        let firstStr = formatter.string(from: first.date)
        let lastStr = formatter.string(from: last.date)
        return firstStr == lastStr ? firstStr : "\(firstStr) – \(lastStr)"
    }
}

private struct ComedianClubRunDisclosure: View {
    @Environment(\.appTheme) private var theme

    let run: Components.Schemas.UpcomingRun
    @Binding var isExpanded: Bool
    let nearbyRadiusMiles: Double?
    let openShow: (Int) -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(spacing: 0) {
            Button {
                withAnimation(.easeInOut(duration: 0.2)) {
                    isExpanded.toggle()
                }
            } label: {
                HStack(spacing: theme.spacing.md) {
                    clubArtwork

                    VStack(alignment: .leading, spacing: 2) {
                        Text(run.clubName)
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .lineLimit(2)
                            .multilineTextAlignment(.leading)
                        Text("\(run.shows.count) \(run.shows.count == 1 ? "show" : "shows") · \(run.dateRangeSummary)")
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    Image(systemName: "chevron.right")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.textSecondary)
                        .rotationEffect(.degrees(isExpanded ? 90 : 0))
                }
                .padding(theme.spacing.md)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            if isExpanded {
                VStack(spacing: theme.spacing.sm) {
                    ForEach(run.shows, id: \.id) { show in
                        Button {
                            openShow(show.id)
                        } label: {
                            ComedianClubRunShowRow(show: show, nearbyRadiusMiles: nearbyRadiusMiles)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, theme.spacing.md)
                .padding(.bottom, theme.spacing.md)
            }
        }
        .background(laughTrack.colors.surface)
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
    }

    @ViewBuilder
    private var clubArtwork: some View {
        let laughTrack = theme.laughTrackTokens
        let url = URL.normalizedExternalURL(run.clubImageUrl.trimmingCharacters(in: .whitespacesAndNewlines))

        Group {
            if let url {
                CachedAsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(laughTrack.colors.surfaceMuted)
                        .overlay {
                            ProgressView().tint(laughTrack.colors.accent)
                        }
                } error: { _ in
                    fallbackArtwork
                }
            } else {
                fallbackArtwork
            }
        }
        .frame(width: 56, height: 56)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private var fallbackArtwork: some View {
        let laughTrack = theme.laughTrackTokens

        return RoundedRectangle(cornerRadius: 12, style: .continuous)
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "building.2.fill")
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }
}

private struct UpcomingShowsFilterPanel: View {
    @Environment(\.appTheme) private var theme

    @Binding var searchText: String
    @Binding var locationFilterText: String
    @Binding var useDateFilter: Bool
    @Binding var dateFilter: Date
    let showsByDate: [Date: Int]

    @State private var isLocationEditorPresented = false
    @State private var isDateEditorPresented = false

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            SearchField(
                title: "Search",
                prompt: "Search this tour",
                text: $searchText,
                showsTitle: false
            )

            SearchToolbar {
                Button {
                    isLocationEditorPresented = true
                } label: {
                    LaughTrackBrowseChip(
                        locationFilterText.isEmpty ? "Location" : locationFilterText,
                        systemImage: "mappin.and.ellipse",
                        tone: locationFilterText.isEmpty ? .neutral : .accent
                    )
                }
                .buttonStyle(.plain)
            } dateScope: {
                Button {
                    isDateEditorPresented = true
                } label: {
                    LaughTrackBrowseChip(
                        useDateFilter ? Self.dateChipLabel(date: dateFilter) : "Any date",
                        systemImage: "calendar",
                        tone: useDateFilter ? .accent : .neutral
                    )
                }
                .buttonStyle(.plain)
            }
        }
        .sheet(isPresented: $isLocationEditorPresented) {
            UpcomingShowsLocationEditor(text: $locationFilterText, isPresented: $isLocationEditorPresented)
        }
        .sheet(isPresented: $isDateEditorPresented) {
            JumpToDateSheet(
                date: $dateFilter,
                isPresented: $isDateEditorPresented,
                showsByDate: showsByDate,
                onApply: { _ in useDateFilter = true },
                onClear: { useDateFilter = false }
            )
        }
    }

    static func dateChipLabel(date: Date) -> String {
        chipDateFormatter.string(from: date)
    }

    private static let chipDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d"
        return formatter
    }()
}

private struct UpcomingShowsLocationEditor: View {
    @Binding var text: String
    @Binding var isPresented: Bool
    @State private var draft: String = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("City, state, or ZIP", text: $draft)
                        .autocorrectionDisabled()
                } footer: {
                    Text("Filters this tour by venue address. Leave blank to clear.")
                }
            }
            .navigationTitle("Location")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Clear") {
                        text = ""
                        isPresented = false
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
                        isPresented = false
                    }
                }
            }
        }
        .onAppear { draft = text }
    }
}

private struct ComedianClubRunShowRow: View {
    @Environment(\.appTheme) private var theme

    let show: Components.Schemas.Show
    let nearbyRadiusMiles: Double?

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.md) {
            showArtwork

            VStack(alignment: .leading, spacing: 2) {
                Text(ShowRow.listTitle(for: show))
                    .font(laughTrack.typography.cardTitle)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
                Text(metadata.joined(separator: " · "))
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(2)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            if isNearby {
                Image(systemName: "location.fill")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .accessibilityLabel("Within saved radius")
            }

            Image(systemName: "chevron.right")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(laughTrack.colors.textSecondary)
        }
        .padding(theme.spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(laughTrack.colors.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
    }

    private var metadata: [String] {
        [
            ShowFormatting.listDate(show.date, timezoneID: show.timezone),
            ShowRow.priceLabel(for: show),
            show.soldOut == true ? "Sold out" : nil
        ].compactMap { $0 }
    }

    private var isNearby: Bool {
        guard let distance = show.distanceMiles, let nearbyRadiusMiles else { return false }
        return distance <= nearbyRadiusMiles
    }

    @ViewBuilder
    private var showArtwork: some View {
        let laughTrack = theme.laughTrackTokens
        let imageURL = show.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? (ShowRow.artworkImageURL(for: show) ?? "")
            : show.imageUrl
        let url = URL.normalizedExternalURL(imageURL.trimmingCharacters(in: .whitespacesAndNewlines))

        Group {
            if let url {
                CachedAsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(laughTrack.colors.surfaceMuted)
                } error: { _ in
                    fallbackArtwork
                }
            } else {
                fallbackArtwork
            }
        }
        .frame(width: 48, height: 48)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private var fallbackArtwork: some View {
        RoundedRectangle(cornerRadius: 12, style: .continuous)
            .fill(theme.laughTrackTokens.colors.surfaceMuted)
            .overlay {
                Image(systemName: "ticket.fill")
                    .font(.system(size: theme.iconSizes.md, weight: .semibold))
                    .foregroundStyle(theme.laughTrackTokens.colors.accentStrong)
            }
    }
}
