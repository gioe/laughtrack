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
                LoadingCard()
                    .padding()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
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
                        LaughTrackCard {
                            VStack(alignment: .leading, spacing: 12) {
                                LaughTrackSectionHeader(title: "Upcoming shows")

                                if let relatedContentMessage = content.relatedContentMessage {
                                    InlineStatusMessage(message: relatedContentMessage)
                                }

                                if content.upcomingShows.isEmpty {
                                    EmptyCard(message: "No upcoming shows are available for this comedian right now.")
                                } else {
                                    UpcomingShowsFilterPanel(
                                        searchText: $searchText,
                                        locationFilterText: $locationFilterText,
                                        useDateFilter: $useDateFilter,
                                        dateFilter: $dateFilter
                                    )

                                    let filtered = filteredUpcomingShows(content.upcomingShows)
                                    if filtered.isEmpty {
                                        EmptyCard(message: "No shows match these filters. Try clearing one.")
                                    } else {
                                        let runs = ComedianClubRun.runs(from: filtered)
                                        VStack(spacing: theme.spacing.sm) {
                                            ForEach(runs) { run in
                                                ComedianClubRunDisclosure(
                                                    run: run,
                                                    isExpanded: Binding(
                                                        get: { expandedRunKeys.contains(run.id) },
                                                        set: { newValue in
                                                            if newValue { expandedRunKeys.insert(run.id) }
                                                            else { expandedRunKeys.remove(run.id) }
                                                        }
                                                    ),
                                                    openShow: { showID in coordinator.open(.show(showID)) }
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        if !content.relatedComedians.isEmpty {
                            LaughTrackCard(tone: .muted) {
                                VStack(alignment: .leading, spacing: 12) {
                                    LaughTrackSectionHeader(title: "Often on the same bill")

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
                    .padding(.horizontal, theme.spacing.lg * 2)
                    .padding(.vertical, theme.spacing.lg)
                    }
                }
            }
        }
        .ignoresSafeArea(.container, edges: .top)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .accessibilityIdentifier(LaughTrackViewTestID.comedianDetailScreen)
        .modifier(EntityDetailNavigationChrome(entity: .comedian))
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

    private func filteredUpcomingShows(_ shows: [Components.Schemas.Show]) -> [Components.Schemas.Show] {
        let search = searchText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let location = locationFilterText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let calendar = Calendar.current

        return shows.filter { show in
            if !search.isEmpty {
                let club = (show.clubName ?? "").lowercased()
                let title = (show.name ?? "").lowercased()
                guard club.contains(search) || title.contains(search) else { return false }
            }
            if !location.isEmpty {
                let address = (show.address ?? "").lowercased()
                guard address.contains(location) else { return false }
            }
            if useDateFilter {
                let timezone = show.timezone.flatMap { TimeZone(identifier: $0) }
                var cal = calendar
                if let timezone { cal.timeZone = timezone }
                guard cal.isDate(show.date, inSameDayAs: dateFilter) else { return false }
            }
            return true
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

struct ComedianClubRun: Identifiable {
    let id: String
    let clubName: String
    let shows: [Components.Schemas.Show]

    static func runs(from shows: [Components.Schemas.Show]) -> [ComedianClubRun] {
        let sorted = shows.sorted { $0.date < $1.date }
        var result: [ComedianClubRun] = []
        var current: [Components.Schemas.Show] = []
        var currentName: String?

        for show in sorted {
            let name = show.clubName ?? "Unknown club"
            if name == currentName {
                current.append(show)
            } else {
                if let cn = currentName, !current.isEmpty {
                    result.append(ComedianClubRun(id: "\(result.count)-\(cn)", clubName: cn, shows: current))
                }
                currentName = name
                current = [show]
            }
        }
        if let cn = currentName, !current.isEmpty {
            result.append(ComedianClubRun(id: "\(result.count)-\(cn)", clubName: cn, shows: current))
        }
        return result
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

    let run: ComedianClubRun
    @Binding var isExpanded: Bool
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
                            ComedianClubRunShowRow(show: show)
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
        let url = run.shows.first.flatMap { URL.normalizedExternalURL($0.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)) }

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

            HStack(spacing: theme.spacing.sm) {
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

                Spacer()
            }
        }
        .sheet(isPresented: $isLocationEditorPresented) {
            UpcomingShowsLocationEditor(text: $locationFilterText, isPresented: $isLocationEditorPresented)
        }
        .sheet(isPresented: $isDateEditorPresented) {
            UpcomingShowsDateEditor(
                useDateFilter: $useDateFilter,
                date: $dateFilter,
                isPresented: $isDateEditorPresented
            )
        }
    }

    static func dateChipLabel(date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d"
        return formatter.string(from: date)
    }
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

private struct UpcomingShowsDateEditor: View {
    @Binding var useDateFilter: Bool
    @Binding var date: Date
    @Binding var isPresented: Bool
    @State private var draftEnabled: Bool = false
    @State private var draftDate: Date = Date()

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Toggle("Filter by date", isOn: $draftEnabled)
                    if draftEnabled {
                        DatePicker("Date", selection: $draftDate, displayedComponents: .date)
                            .datePickerStyle(.graphical)
                    }
                }
            }
            .navigationTitle("Date")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Clear") {
                        useDateFilter = false
                        isPresented = false
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        useDateFilter = draftEnabled
                        date = draftDate
                        isPresented = false
                    }
                }
            }
        }
        .onAppear {
            draftEnabled = useDateFilter
            draftDate = date
        }
    }
}

private struct ComedianClubRunShowRow: View {
    @Environment(\.appTheme) private var theme

    let show: Components.Schemas.Show

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.md) {
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
}
