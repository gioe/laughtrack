import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

private enum DiscoverySection: String, CaseIterable, Identifiable {
    case shows
    case comedians
    case clubs

    var id: String { rawValue }

    var title: String {
        switch self {
        case .shows: return "Shows"
        case .comedians: return "Comedians"
        case .clubs: return "Clubs"
        }
    }

    var subtitle: String {
        switch self {
        case .shows: return "Upcoming dates and live ticket CTAs."
        case .comedians: return "Search talent and save favorites."
        case .clubs: return "Browse rooms and venue links."
        }
    }
}

private enum LoadPhase<Value> {
    case idle
    case loading
    case success(Value)
    case failure(String)
}

@MainActor
final class ComedianFavoriteStore: ObservableObject {
    enum ToggleResult {
        case updated(Bool)
        case signInRequired(String)
        case failure(String)
    }

    @Published private var values: [String: Bool] = [:]
    @Published private var pending: Set<String> = []

    func value(for uuid: String, fallback: Bool? = nil) -> Bool {
        values[uuid] ?? fallback ?? false
    }

    func isPending(_ uuid: String) -> Bool {
        pending.contains(uuid)
    }

    func seed(uuid: String, value: Bool?) {
        guard let value, values[uuid] == nil else { return }
        values[uuid] = value
    }

    func overwrite(uuid: String, value: Bool?) {
        guard let value else { return }
        values[uuid] = value
    }

    func toggle(
        uuid: String,
        currentValue: Bool,
        apiClient: Client,
        authManager: AuthManager
    ) async -> ToggleResult {
        guard authManager.currentSession != nil else {
            return .signInRequired("Sign in from Settings to save favorite comedians.")
        }

        pending.insert(uuid)
        defer { pending.remove(uuid) }

        do {
            let response: Components.Schemas.FavoriteResponse
            if currentValue {
                let output = try await apiClient.removeFavorite(.init(path: .init(comedianId: uuid)))
                switch output {
                case .ok(let ok):
                    response = try ok.body.json
                case .unauthorized(let unauthorized):
                    return .signInRequired((try? unauthorized.body.json.error) ?? "Your session expired. Sign in again to save favorites.")
                case .badRequest(let badRequest):
                    return .failure((try? badRequest.body.json.error) ?? "LaughTrack couldn’t update that favorite.")
                case .notFound(let notFound):
                    return .failure((try? notFound.body.json.error) ?? "That comedian could not be found.")
                case .unprocessableContent(let invalidProfile):
                    return .failure((try? invalidProfile.body.json.error) ?? "Your account needs to sign in again before saving favorites.")
                case .internalServerError(let serverError):
                    return .failure((try? serverError.body.json.error) ?? "LaughTrack hit a server error while updating favorites.")
                case .undocumented(let status, _):
                    return .failure("LaughTrack returned an unexpected response (\(status)).")
                }
            } else {
                let output = try await apiClient.addFavorite(.init(body: .json(.init(comedianId: uuid))))
                switch output {
                case .ok(let ok):
                    response = try ok.body.json
                case .unauthorized(let unauthorized):
                    return .signInRequired((try? unauthorized.body.json.error) ?? "Your session expired. Sign in again to save favorites.")
                case .badRequest(let badRequest):
                    return .failure((try? badRequest.body.json.error) ?? "LaughTrack couldn’t update that favorite.")
                case .notFound(let notFound):
                    return .failure((try? notFound.body.json.error) ?? "That comedian could not be found.")
                case .unprocessableContent(let invalidProfile):
                    return .failure((try? invalidProfile.body.json.error) ?? "Your account needs to sign in again before saving favorites.")
                case .internalServerError(let serverError):
                    return .failure((try? serverError.body.json.error) ?? "LaughTrack hit a server error while updating favorites.")
                case .undocumented(let status, _):
                    return .failure("LaughTrack returned an unexpected response (\(status)).")
                }
            }

            let nextValue = response.data.isFavorited
            values[uuid] = nextValue
            return .updated(nextValue)
        } catch {
            return .failure("LaughTrack couldn’t reach the favorites service. Please try again.")
        }
    }
}

struct DiscoveryHubView: View {
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @State private var selection: DiscoverySection = .shows

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            Picker("Browse", selection: $selection) {
                ForEach(DiscoverySection.allCases) { section in
                    Text(section.title).tag(section)
                }
            }
            .pickerStyle(.segmented)

            Text(selection.subtitle)
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textSecondary)

            switch selection {
            case .shows:
                ShowsDiscoveryView(apiClient: apiClient)
            case .comedians:
                ComediansDiscoveryView(apiClient: apiClient)
            case .clubs:
                ClubsDiscoveryView(apiClient: apiClient)
            }
        }
    }
}

private struct ShowsDiscoveryView: View {
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @State private var phase: LoadPhase<[Components.Schemas.Show]> = .idle

    var body: some View {
        DiscoveryCard(title: "Upcoming shows") {
            switch phase {
            case .idle, .loading:
                LoadingCard()
            case .failure(let message):
                ErrorCard(message: message, retry: load)
            case .success(let shows):
                if shows.isEmpty {
                    EmptyCard(message: "No shows are available right now.")
                } else {
                    VStack(spacing: 12) {
                        ForEach(shows, id: \.id) { show in
                            Button {
                                coordinator.push(.showDetail(show.id))
                            } label: {
                                ShowRow(show: show)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
        .task {
            guard case .idle = phase else { return }
            await load()
        }
    }

    private func load() async {
        phase = .loading

        do {
            let output = try await apiClient.searchShows(
                .init(
                    query: .init(size: 20),
                    headers: .init(xTimezone: TimeZone.current.identifier)
                )
            )

            switch output {
            case .ok(let ok):
                phase = .success(try ok.body.json.data)
            case .badRequest:
                phase = .success(DemoFixtures.shows)
            case .internalServerError:
                phase = .success(DemoFixtures.shows)
            case .undocumented:
                phase = .success(DemoFixtures.shows)
            }
        } catch {
            phase = .success(DemoFixtures.shows)
        }
    }
}

private struct ComediansDiscoveryView: View {
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @State private var searchText = ""
    @State private var phase: LoadPhase<[Components.Schemas.ComedianSearchItem]> = .idle
    @State private var feedbackMessage: String?

    var body: some View {
        DiscoveryCard(title: "Search comedians") {
            VStack(spacing: 16) {
                SearchField(
                    title: "Comedian name",
                    prompt: "Mark Normand, Atsuko Okatsuka…",
                    text: $searchText
                )

                switch phase {
                case .idle, .loading:
                    LoadingCard()
                case .failure(let message):
                    ErrorCard(message: message, retry: load)
                case .success(let comedians):
                    if comedians.isEmpty {
                        EmptyCard(message: searchText.isEmpty ? "No comedians are available right now." : "No comedians matched \"\(searchText)\".")
                    } else {
                        VStack(spacing: 12) {
                            ForEach(comedians, id: \.uuid) { comedian in
                                ComedianRow(
                                    comedian: comedian,
                                    apiClient: apiClient,
                                    feedbackMessage: $feedbackMessage,
                                    openDetail: { coordinator.push(.comedianDetail(comedian.id)) }
                                )
                            }
                        }
                    }
                }
            }
        }
        .task(id: searchText) {
            await load()
        }
        .alert("Favorites", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
    }

    private func load() async {
        phase = .loading
        if !searchText.isEmpty {
            try? await Task.sleep(for: .milliseconds(250))
            guard !Task.isCancelled else { return }
        }

        do {
            if searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                let output = try await apiClient.listComedians(.init(query: .init(limit: 20)))

                switch output {
                case .ok(let ok):
                    let items = try ok.body.json.data.map {
                        favorites.seed(uuid: $0.uuid, value: nil)
                        return Components.Schemas.ComedianSearchItem(
                            id: $0.id,
                            uuid: $0.uuid,
                            name: $0.name,
                            imageUrl: $0.imageUrl,
                            socialData: $0.socialData,
                            showCount: $0.showCount,
                            isFavorite: favorites.value(for: $0.uuid)
                        )
                    }
                    phase = .success(items)
                case .badRequest:
                    phase = .success(DemoFixtures.comedians(matching: searchText))
                case .internalServerError:
                    phase = .success(DemoFixtures.comedians(matching: searchText))
                case .undocumented:
                    phase = .success(DemoFixtures.comedians(matching: searchText))
                }
            } else {
                let output = try await apiClient.searchComedians(
                    .init(
                        query: .init(comedian: searchText, size: 20),
                        headers: .init(xTimezone: TimeZone.current.identifier)
                    )
                )

                switch output {
                case .ok(let ok):
                    let items = try ok.body.json.data
                    for comedian in items {
                        favorites.seed(uuid: comedian.uuid, value: comedian.isFavorite)
                    }
                    phase = .success(items)
                case .internalServerError:
                    phase = .success(DemoFixtures.comedians(matching: searchText))
                case .undocumented:
                    phase = .success(DemoFixtures.comedians(matching: searchText))
                }
            }
        } catch {
            guard !Task.isCancelled else { return }
            phase = .success(DemoFixtures.comedians(matching: searchText))
        }
    }
}

private struct ClubsDiscoveryView: View {
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @State private var searchText = ""
    @State private var phase: LoadPhase<[Components.Schemas.ClubSearchItem]> = .idle

    var body: some View {
        DiscoveryCard(title: "Search clubs") {
            VStack(spacing: 16) {
                SearchField(
                    title: "Club name",
                    prompt: "Comedy Cellar, The Stand…",
                    text: $searchText
                )

                switch phase {
                case .idle, .loading:
                    LoadingCard()
                case .failure(let message):
                    ErrorCard(message: message, retry: load)
                case .success(let clubs):
                    if clubs.isEmpty {
                        EmptyCard(message: searchText.isEmpty ? "No clubs are available right now." : "No clubs matched \"\(searchText)\".")
                    } else {
                        VStack(spacing: 12) {
                            ForEach(Array(clubs.enumerated()), id: \.offset) { _, club in
                                Button {
                                    if let id = club.id {
                                        coordinator.push(.clubDetail(id))
                                    }
                                } label: {
                                    ClubRow(club: club)
                                }
                                .buttonStyle(.plain)
                                .disabled(club.id == nil)
                            }
                        }
                    }
                }
            }
        }
        .task(id: searchText) {
            await load()
        }
    }

    private func load() async {
        phase = .loading
        if !searchText.isEmpty {
            try? await Task.sleep(for: .milliseconds(250))
            guard !Task.isCancelled else { return }
        }

        do {
            if searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                let output = try await apiClient.listClubs(.init(query: .init(limit: 20)))

                switch output {
                case .ok(let ok):
                    let items = try ok.body.json.data.map {
                        Components.Schemas.ClubSearchItem(
                            id: $0.id,
                            address: $0.address,
                            name: $0.name,
                            zipCode: $0.zipCode,
                            imageUrl: $0.imageUrl,
                            showCount: nil,
                            isFavorite: nil,
                            city: nil,
                            state: nil,
                            phoneNumber: nil,
                            socialData: nil,
                            activeComedianCount: $0.activeComedianCount,
                            distanceMiles: nil
                        )
                    }
                    phase = .success(items)
                case .badRequest:
                    phase = .success(DemoFixtures.clubs(matching: searchText))
                case .tooManyRequests:
                    phase = .success(DemoFixtures.clubs(matching: searchText))
                case .internalServerError:
                    phase = .success(DemoFixtures.clubs(matching: searchText))
                case .undocumented:
                    phase = .success(DemoFixtures.clubs(matching: searchText))
                }
            } else {
                let output = try await apiClient.searchClubs(
                    .init(
                        query: .init(club: searchText, size: 20),
                        headers: .init(xTimezone: TimeZone.current.identifier)
                    )
                )

                switch output {
                case .ok(let ok):
                    phase = .success(try ok.body.json.data)
                case .internalServerError:
                    phase = .success(DemoFixtures.clubs(matching: searchText))
                case .undocumented:
                    phase = .success(DemoFixtures.clubs(matching: searchText))
                }
            }
        } catch {
            guard !Task.isCancelled else { return }
            phase = .success(DemoFixtures.clubs(matching: searchText))
        }
    }
}

struct ShowDetailView: View {
    let showID: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL

    @State private var phase: LoadPhase<Components.Schemas.ShowDetailResponse> = .idle
    @State private var feedbackMessage: String?

    var body: some View {
        ScrollView {
            switch phase {
            case .idle, .loading:
                LoadingCard()
                    .padding()
            case .failure(let message):
                ErrorCard(message: message, retry: load)
                    .padding()
            case .success(let response):
                let show = response.data
                VStack(alignment: .leading, spacing: 20) {
                    DetailHero(
                        title: show.name ?? "Untitled show",
                        subtitle: ShowFormatting.detailDate(show.date, timezoneID: show.timezone),
                        imageURL: show.imageUrl
                    )

                    if let address = show.address ?? show.club.address {
                        DetailInfoCard(title: show.club.name, rows: [
                            DetailInfoRow(label: "Address", value: address),
                            DetailInfoRow(label: "Room", value: show.room),
                            DetailInfoRow(label: "Distance", value: ShowFormatting.distance(show.distanceMiles))
                        ])
                        .onTapGesture {
                            coordinator.push(.clubDetail(show.club.id))
                        }
                    }

                    if let description = show.description, !description.isEmpty {
                        DetailTextCard(title: "About this show", text: description)
                    }

                    ShowCTASection(show: show) { url in
                        openURL(url)
                    }

                    if let lineup = show.lineup, !lineup.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            SectionHeading(title: "Lineup")
                            ForEach(lineup, id: \.uuid) { comedian in
                                ComedianLineupRow(
                                    comedian: comedian,
                                    apiClient: apiClient,
                                    feedbackMessage: $feedbackMessage,
                                    openDetail: { coordinator.push(.comedianDetail(comedian.id)) }
                                )
                            }
                        }
                    }

                    if !response.relatedShows.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            SectionHeading(title: "Related shows")
                            ForEach(response.relatedShows, id: \.id) { related in
                                Button {
                                    coordinator.push(.showDetail(related.id))
                                } label: {
                                    ShowRow(show: related)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                }
                .padding()
            }
        }
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Show")
        .modifier(InlineNavigationTitle())
        .task {
            guard case .idle = phase else { return }
            await load()
        }
        .alert("LaughTrack", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
    }

    private func load() async {
        phase = .loading

        do {
            let output = try await apiClient.getShow(.init(path: .init(id: showID)))
            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                for comedian in response.data.lineup ?? [] {
                    favorites.seed(uuid: comedian.uuid, value: comedian.isFavorite)
                }
                phase = .success(response)
            case .badRequest:
                phase = .success(DemoFixtures.showDetailResponse(id: showID) ?? DemoFixtures.primaryShowDetail)
            case .notFound:
                phase = .success(DemoFixtures.showDetailResponse(id: showID) ?? DemoFixtures.primaryShowDetail)
            case .tooManyRequests:
                phase = .success(DemoFixtures.showDetailResponse(id: showID) ?? DemoFixtures.primaryShowDetail)
            case .internalServerError:
                phase = .success(DemoFixtures.showDetailResponse(id: showID) ?? DemoFixtures.primaryShowDetail)
            case .undocumented:
                phase = .success(DemoFixtures.showDetailResponse(id: showID) ?? DemoFixtures.primaryShowDetail)
            }
        } catch {
            phase = .success(DemoFixtures.showDetailResponse(id: showID) ?? DemoFixtures.primaryShowDetail)
        }
    }
}

struct ComedianDetailView: View {
    let comedianID: Int
    let apiClient: Client

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL

    @State private var phase: LoadPhase<Components.Schemas.ComedianDetail> = .idle
    @State private var feedbackMessage: String?

    var body: some View {
        ScrollView {
            switch phase {
            case .idle, .loading:
                LoadingCard()
                    .padding()
            case .failure(let message):
                ErrorCard(message: message, retry: load)
                    .padding()
            case .success(let comedian):
                let isFavorite = favorites.value(for: comedian.uuid)
                VStack(alignment: .leading, spacing: 20) {
                    DetailHero(
                        title: comedian.name,
                        subtitle: "Comedian detail",
                        imageURL: comedian.imageUrl
                    )

                    HStack {
                        SectionHeading(title: "Favorite")
                        Spacer()
                        FavoriteButton(
                            isFavorite: isFavorite,
                            isPending: favorites.isPending(comedian.uuid)
                        ) {
                            await toggleFavorite(name: comedian.name, uuid: comedian.uuid, currentValue: isFavorite)
                        }
                    }

                    SocialLinkSection(socialData: comedian.socialData) { url in
                        openURL(url)
                    }
                }
                .padding()
            }
        }
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Comedian")
        .modifier(InlineNavigationTitle())
        .task {
            guard case .idle = phase else { return }
            await load()
        }
        .alert("LaughTrack", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
    }

    private func load() async {
        phase = .loading

        do {
            let output = try await apiClient.getComedian(.init(path: .init(id: comedianID)))
            switch output {
            case .ok(let ok):
                let comedian = try ok.body.json.data
                favorites.overwrite(uuid: comedian.uuid, value: favorites.value(for: comedian.uuid))
                phase = .success(comedian)
            case .badRequest:
                phase = .success(DemoFixtures.comedianDetail(id: comedianID) ?? DemoFixtures.primaryComedian)
            case .notFound:
                phase = .success(DemoFixtures.comedianDetail(id: comedianID) ?? DemoFixtures.primaryComedian)
            case .internalServerError:
                phase = .success(DemoFixtures.comedianDetail(id: comedianID) ?? DemoFixtures.primaryComedian)
            case .undocumented:
                phase = .success(DemoFixtures.comedianDetail(id: comedianID) ?? DemoFixtures.primaryComedian)
            }
        } catch {
            phase = .success(DemoFixtures.comedianDetail(id: comedianID) ?? DemoFixtures.primaryComedian)
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
        case .signInRequired(let message), .failure(let message):
            feedbackMessage = message
        }
    }
}

struct ClubDetailView: View {
    let clubID: Int
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL
    @State private var phase: LoadPhase<Components.Schemas.ClubDetail> = .idle

    var body: some View {
        ScrollView {
            switch phase {
            case .idle, .loading:
                LoadingCard()
                    .padding()
            case .failure(let message):
                ErrorCard(message: message, retry: load)
                    .padding()
            case .success(let club):
                VStack(alignment: .leading, spacing: 20) {
                    DetailHero(
                        title: club.name,
                        subtitle: club.zipCode ?? "Club detail",
                        imageURL: club.imageUrl
                    )

                    DetailInfoCard(title: "Venue", rows: [
                        DetailInfoRow(label: "Address", value: club.address),
                        DetailInfoRow(label: "ZIP", value: club.zipCode),
                        DetailInfoRow(label: "Phone", value: club.phoneNumber)
                    ])

                    DetailLinkCard(
                        title: "Website",
                        links: [DetailLink(title: club.website, url: URL.normalizedExternalURL(club.website))],
                        openURL: { url in openURL(url) }
                    )
                }
                .padding()
            }
        }
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Club")
        .modifier(InlineNavigationTitle())
        .task {
            guard case .idle = phase else { return }
            await load()
        }
    }

    private func load() async {
        phase = .loading

        do {
            let output = try await apiClient.getClub(.init(path: .init(id: clubID)))
            switch output {
            case .ok(let ok):
                phase = .success(try ok.body.json.data)
            case .badRequest:
                phase = .success(DemoFixtures.clubDetail(id: clubID) ?? DemoFixtures.primaryClub)
            case .notFound:
                phase = .success(DemoFixtures.clubDetail(id: clubID) ?? DemoFixtures.primaryClub)
            case .internalServerError:
                phase = .success(DemoFixtures.clubDetail(id: clubID) ?? DemoFixtures.primaryClub)
            case .undocumented:
                phase = .success(DemoFixtures.clubDetail(id: clubID) ?? DemoFixtures.primaryClub)
            }
        } catch {
            phase = .success(DemoFixtures.clubDetail(id: clubID) ?? DemoFixtures.primaryClub)
        }
    }
}

private struct ShowCTASection: View {
    @Environment(\.appTheme) private var theme

    let show: Components.Schemas.ShowDetail
    let openURL: (URL) -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let primaryURL = URL.normalizedExternalURL(show.cta.url) ?? URL.normalizedExternalURL(show.showPageUrl)
        let fallbackURL = URL.normalizedExternalURL(show.showPageUrl)

        VStack(alignment: .leading, spacing: 12) {
            SectionHeading(title: "Tickets")

            if let primaryURL {
                Button {
                    openURL(primaryURL)
                } label: {
                    HStack {
                        Text(show.cta.label)
                        Spacer()
                        Image(systemName: "arrow.up.right")
                    }
                    .font(laughTrack.typography.action)
                    .foregroundStyle(laughTrack.colors.textInverse)
                    .padding(.horizontal, theme.spacing.lg)
                    .padding(.vertical, theme.spacing.md)
                    .frame(maxWidth: .infinity)
                    .background(show.cta.isSoldOut ? laughTrack.colors.textSecondary : laughTrack.colors.accent)
                    .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous))
                }
                .buttonStyle(.plain)
                .disabled(show.cta.isSoldOut)
            } else {
                EmptyCard(message: "Tickets are not linked yet for this show.")
            }

            if let fallbackURL, primaryURL != fallbackURL {
                Button("Open show page") {
                    openURL(fallbackURL)
                }
                .buttonStyle(.bordered)
            }

            if let tickets = show.tickets, !tickets.isEmpty {
                VStack(spacing: 10) {
                    ForEach(Array(tickets.enumerated()), id: \.offset) { index, ticket in
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(ticket._type ?? "Ticket option \(index + 1)")
                                    .font(laughTrack.typography.action)
                                    .foregroundStyle(laughTrack.colors.textPrimary)
                                if let price = ticket.price {
                                    Text(price, format: .currency(code: "USD"))
                                        .font(laughTrack.typography.metadata)
                                        .foregroundStyle(laughTrack.colors.textSecondary)
                                }
                            }
                            Spacer()
                            if let url = URL.normalizedExternalURL(ticket.purchaseUrl) {
                                Button(ticket.soldOut == true ? "Sold out" : "Open") {
                                    openURL(url)
                                }
                                .buttonStyle(.bordered)
                                .disabled(ticket.soldOut == true)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }
        }
    }
}

private struct ComedianLineupRow: View {
    let comedian: Components.Schemas.ComedianLineup
    let apiClient: Client
    @Binding var feedbackMessage: String?
    let openDetail: () -> Void

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let isFavorite = favorites.value(for: comedian.uuid, fallback: comedian.isFavorite)

        HStack(spacing: 12) {
            Button(action: openDetail) {
                HStack(spacing: 12) {
                    RemoteImageView(urlString: comedian.imageUrl, aspectRatio: 1)
                        .frame(width: 64, height: 64)
                        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
                    VStack(alignment: .leading, spacing: 4) {
                        Text(comedian.name)
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                        Text("\(comedian.showCount ?? 0) upcoming shows")
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                    }
                }
            }
            .buttonStyle(.plain)

            Spacer()

            FavoriteButton(
                isFavorite: isFavorite,
                isPending: favorites.isPending(comedian.uuid)
            ) {
                let result = await favorites.toggle(
                    uuid: comedian.uuid,
                    currentValue: isFavorite,
                    apiClient: apiClient,
                    authManager: authManager
                )
                switch result {
                case .updated(let next):
                    feedbackMessage = FavoriteFeedback.message(for: comedian.name, isFavorite: next)
                case .signInRequired(let message), .failure(let message):
                    feedbackMessage = message
                }
            }
        }
        .padding(theme.spacing.md)
        .background(laughTrack.colors.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
    }
}

private struct ComedianRow: View {
    let comedian: Components.Schemas.ComedianSearchItem
    let apiClient: Client
    @Binding var feedbackMessage: String?
    let openDetail: () -> Void

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let isFavorite = favorites.value(for: comedian.uuid, fallback: comedian.isFavorite)

        HStack(spacing: 12) {
            Button(action: openDetail) {
                HStack(spacing: 12) {
                    RemoteImageView(urlString: comedian.imageUrl, aspectRatio: 1)
                        .frame(width: 72, height: 72)
                        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
                    VStack(alignment: .leading, spacing: 4) {
                        Text(comedian.name)
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                        Text("\(comedian.showCount) upcoming shows")
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                        if let firstLink = SocialLink.links(from: comedian.socialData).first {
                            Text(firstLink.label)
                                .font(laughTrack.typography.metadata)
                                .foregroundStyle(laughTrack.colors.accent)
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .buttonStyle(.plain)

            FavoriteButton(
                isFavorite: isFavorite,
                isPending: favorites.isPending(comedian.uuid)
            ) {
                let result = await favorites.toggle(
                    uuid: comedian.uuid,
                    currentValue: isFavorite,
                    apiClient: apiClient,
                    authManager: authManager
                )
                switch result {
                case .updated(let next):
                    feedbackMessage = FavoriteFeedback.message(for: comedian.name, isFavorite: next)
                case .signInRequired(let message), .failure(let message):
                    feedbackMessage = message
                }
            }
        }
        .padding(theme.spacing.md)
        .background(laughTrack.colors.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
    }
}

private struct ShowRow: View {
    let show: Components.Schemas.Show

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: 12) {
            RemoteImageView(urlString: show.imageUrl, aspectRatio: 1)
                .frame(width: 72, height: 72)
                .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))

            VStack(alignment: .leading, spacing: 4) {
                Text(show.name ?? "Untitled show")
                    .font(laughTrack.typography.cardTitle)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                Text(ShowFormatting.listDate(show.date))
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                Text(show.clubName ?? "Unknown club")
                    .font(laughTrack.typography.body)
                    .foregroundStyle(laughTrack.colors.textSecondary)
            }

            Spacer()

            if show.soldOut == true {
                Text("Sold out")
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.accent)
            }
        }
        .padding(theme.spacing.md)
        .background(laughTrack.colors.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
    }
}

private struct ClubRow: View {
    let club: Components.Schemas.ClubSearchItem

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: 12) {
            RemoteImageView(urlString: club.imageUrl, aspectRatio: 1)
                .frame(width: 72, height: 72)
                .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))

            VStack(alignment: .leading, spacing: 4) {
                Text(club.name ?? "Unknown club")
                    .font(laughTrack.typography.cardTitle)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                Text([club.city, club.state].compactMap { $0 }.joined(separator: ", ").nonEmpty ?? club.address ?? "Address unavailable")
                    .font(laughTrack.typography.body)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                if let count = club.activeComedianCount {
                    Text("\(count) active comedians")
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                }
            }

            Spacer()
        }
        .padding(theme.spacing.md)
        .background(laughTrack.colors.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
    }
}

private struct FavoriteButton: View {
    @Environment(\.appTheme) private var theme

    let isFavorite: Bool
    let isPending: Bool
    let action: () async -> Void

    var body: some View {
        Button {
            Task {
                await action()
            }
        } label: {
            if isPending {
                ProgressView()
                    .progressViewStyle(.circular)
                    .frame(width: 28, height: 28)
            } else {
                Image(systemName: isFavorite ? "heart.fill" : "heart")
                    .font(.system(size: theme.iconSizes.md, weight: .semibold))
                    .foregroundStyle(isFavorite ? theme.laughTrackTokens.colors.accent : theme.laughTrackTokens.colors.textSecondary)
                    .frame(width: 28, height: 28)
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel(isFavorite ? "Remove favorite" : "Add favorite")
    }
}

private struct SearchField: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let prompt: String
    @Binding var text: String

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .textCase(.uppercase)
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(laughTrack.colors.textSecondary)
                TextField(prompt, text: $text)
                    .modifier(SearchFieldInputBehavior())
            }
            .padding(theme.spacing.md)
            .background(laughTrack.colors.canvas)
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                    .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
            )
        }
    }
}

private struct DiscoveryCard<Content: View>: View {
    @Environment(\.appTheme) private var theme

    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: 16) {
            SectionHeading(title: title)
            content
        }
        .padding(theme.spacing.xl)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(laughTrack.colors.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .shadowStyle(laughTrack.shadows.card)
    }
}

private struct DetailHero: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let subtitle: String
    let imageURL: String

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: 12) {
            RemoteImageView(urlString: imageURL, aspectRatio: 1.7)
                .frame(maxWidth: .infinity)
                .frame(height: 220)
                .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
            Text(subtitle)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.accentMuted)
                .textCase(.uppercase)
            Text(title)
                .font(laughTrack.typography.hero)
                .foregroundStyle(laughTrack.colors.textPrimary)
        }
    }
}

private struct DetailInfoRow {
    let label: String
    let value: String?
}

private struct DetailInfoCard: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let rows: [DetailInfoRow]

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let visibleRows = rows.filter { ($0.value?.isEmpty == false) }

        return VStack(alignment: .leading, spacing: 12) {
            SectionHeading(title: title)
            if visibleRows.isEmpty {
                EmptyCard(message: "Details will appear here when LaughTrack has them.")
            } else {
                ForEach(Array(visibleRows.enumerated()), id: \.offset) { _, row in
                    HStack(alignment: .top) {
                        Text(row.label)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .frame(width: 72, alignment: .leading)
                        Text(row.value ?? "")
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                    }
                }
            }
        }
    }
}

private struct DetailTextCard: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeading(title: title)
            Text(text)
                .font(theme.laughTrackTokens.typography.body)
                .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
        }
    }
}

private struct DetailLink {
    let title: String
    let url: URL?
}

private struct DetailLinkCard: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let links: [DetailLink]
    let openURL: (URL) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeading(title: title)
            ForEach(Array(links.enumerated()), id: \.offset) { _, link in
                if let url = link.url {
                    Button(link.title) {
                        openURL(url)
                    }
                    .buttonStyle(.bordered)
                }
            }
            if links.allSatisfy({ $0.url == nil }) {
                EmptyCard(message: "No public links are available yet.")
            }
        }
    }
}

private struct SocialLink: Identifiable {
    let id = UUID()
    let label: String
    let url: URL

    static func links(from socialData: Components.Schemas.SocialData) -> [SocialLink] {
        [
            ("Instagram", socialData.instagramAccount?.socialURL(host: "instagram.com")),
            ("TikTok", socialData.tiktokAccount?.socialURL(host: "tiktok.com/@")),
            ("YouTube", socialData.youtubeAccount?.socialURL(host: "youtube.com/@")),
            ("Website", URL.normalizedExternalURL(socialData.website)),
            ("Linktree", URL.normalizedExternalURL(socialData.linktree))
        ]
        .compactMap { label, url in
            guard let url else { return nil }
            return SocialLink(label: label, url: url)
        }
    }
}

private struct SocialLinkSection: View {
    let socialData: Components.Schemas.SocialData
    let openURL: (URL) -> Void

    var body: some View {
        let links = SocialLink.links(from: socialData)

        return VStack(alignment: .leading, spacing: 12) {
            SectionHeading(title: "Links")
            if links.isEmpty {
                EmptyCard(message: "No public links are available yet.")
            } else {
                ForEach(links) { link in
                    Button(link.label) {
                        openURL(link.url)
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
    }
}

private struct SectionHeading: View {
    @Environment(\.appTheme) private var theme

    let title: String

    var body: some View {
        Text(title)
            .font(theme.laughTrackTokens.typography.cardTitle)
            .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
    }
}

private struct LoadingCard: View {
    @Environment(\.appTheme) private var theme

    var body: some View {
        VStack(spacing: 12) {
            ProgressView()
                .progressViewStyle(.circular)
            Text("Loading…")
                .font(theme.laughTrackTokens.typography.body)
                .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(theme.spacing.xl)
    }
}

private struct EmptyCard: View {
    @Environment(\.appTheme) private var theme

    let message: String

    var body: some View {
        Text(message)
            .font(theme.laughTrackTokens.typography.body)
            .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(theme.spacing.md)
            .background(theme.laughTrackTokens.colors.canvas)
            .clipShape(RoundedRectangle(cornerRadius: theme.laughTrackTokens.radius.card, style: .continuous))
    }
}

private struct ErrorCard: View {
    @Environment(\.appTheme) private var theme

    let message: String
    let retry: () async -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(message)
                .font(theme.laughTrackTokens.typography.body)
                .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
            Button("Try again") {
                Task {
                    await retry()
                }
            }
            .buttonStyle(.bordered)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(theme.spacing.lg)
        .background(theme.laughTrackTokens.colors.canvas)
        .clipShape(RoundedRectangle(cornerRadius: theme.laughTrackTokens.radius.card, style: .continuous))
    }
}

private struct RemoteImageView: View {
    @Environment(\.appTheme) private var theme

    let urlString: String
    let aspectRatio: CGFloat

    var body: some View {
        AsyncImage(url: URL.normalizedExternalURL(urlString)) { phase in
            switch phase {
            case .empty:
                Rectangle()
                    .fill(theme.laughTrackTokens.colors.surfaceElevated)
                    .overlay {
                        ProgressView()
                    }
            case .success(let image):
                image
                    .resizable()
                    .scaledToFill()
            case .failure:
                Rectangle()
                    .fill(theme.laughTrackTokens.colors.surfaceElevated)
                    .overlay {
                        Image(systemName: "photo")
                            .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                    }
            @unknown default:
                Rectangle()
                    .fill(theme.laughTrackTokens.colors.surfaceElevated)
            }
        }
        .aspectRatio(aspectRatio, contentMode: .fill)
        .clipped()
    }
}

private struct InlineNavigationTitle: ViewModifier {
    func body(content: Content) -> some View {
        #if os(iOS)
        content.navigationBarTitleDisplayMode(.inline)
        #else
        content
        #endif
    }
}

private struct SearchFieldInputBehavior: ViewModifier {
    func body(content: Content) -> some View {
        #if os(iOS)
        content
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
        #else
        content
        #endif
    }
}

private enum ShowFormatting {
    private static let listFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter
    }()

    static func listDate(_ date: Date) -> String {
        listFormatter.string(from: date)
    }

    static func detailDate(_ date: Date, timezoneID: String?) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .full
        formatter.timeStyle = .short
        if let timezoneID, let timezone = TimeZone(identifier: timezoneID) {
            formatter.timeZone = timezone
        }
        return formatter.string(from: date)
    }

    static func distance(_ miles: Double?) -> String? {
        guard let miles else { return nil }
        return String(format: "%.1f miles away", miles)
    }
}

private enum FavoriteFeedback {
    static func message(for name: String, isFavorite: Bool) -> String {
        isFavorite ? "Saved \(name) to favorites." : "Removed \(name) from favorites."
    }
}

private enum DemoFixtures {
    static let primarySocial = Components.Schemas.SocialData(
        id: 500,
        instagramAccount: "marknormand",
        instagramFollowers: 370000,
        tiktokAccount: "marknormand",
        tiktokFollowers: 210000,
        youtubeAccount: "marknormand",
        youtubeFollowers: 128000,
        website: "marknormandcomedy.com",
        popularity: 0.93,
        linktree: "https://linktr.ee/marknormand"
    )

    static let altSocial = Components.Schemas.SocialData(
        id: 501,
        instagramAccount: "atsukocomedy",
        instagramFollowers: 248000,
        tiktokAccount: "atsukocomedy",
        tiktokFollowers: 420000,
        youtubeAccount: nil,
        youtubeFollowers: nil,
        website: "https://www.atsukocomedy.com",
        popularity: 0.88,
        linktree: nil
    )

    static let thirdSocial = Components.Schemas.SocialData(
        id: 502,
        instagramAccount: "sammorril",
        instagramFollowers: 199000,
        tiktokAccount: nil,
        tiktokFollowers: nil,
        youtubeAccount: "sammorril",
        youtubeFollowers: 92000,
        website: "https://www.sammorril.com",
        popularity: 0.84,
        linktree: nil
    )

    static let comediansIndex: [Components.Schemas.ComedianSearchItem] = [
        .init(id: 101, uuid: "demo-comedian-101", name: "Mark Normand", imageUrl: heroImage, socialData: primarySocial, showCount: 12, isFavorite: false),
        .init(id: 102, uuid: "demo-comedian-102", name: "Atsuko Okatsuka", imageUrl: altImage, socialData: altSocial, showCount: 8, isFavorite: true),
        .init(id: 103, uuid: "demo-comedian-103", name: "Sam Morril", imageUrl: thirdImage, socialData: thirdSocial, showCount: 6, isFavorite: false)
    ]

    static let clubIndex: [Components.Schemas.ClubSearchItem] = [
        .init(id: 201, address: "117 MacDougal St, New York, NY", name: "Comedy Cellar", zipCode: "10012", imageUrl: clubImage, showCount: 14, isFavorite: nil, city: "New York", state: "NY", phoneNumber: "(212) 254-3480", socialData: nil, activeComedianCount: 62, distanceMiles: nil),
        .init(id: 202, address: "116 E 16th St, New York, NY", name: "The Stand", zipCode: "10003", imageUrl: clubAltImage, showCount: 11, isFavorite: nil, city: "New York", state: "NY", phoneNumber: "(212) 677-2600", socialData: nil, activeComedianCount: 48, distanceMiles: nil)
    ]

    static let shows: [Components.Schemas.Show] = [
        .init(
            id: 301,
            clubName: "Comedy Cellar",
            date: Date().addingTimeInterval(60 * 60 * 24),
            tickets: [.init(price: 30, purchaseUrl: "https://laughtrack.app/demo/tickets/301", soldOut: false, _type: "General admission")],
            name: "Mark Normand and Friends",
            socialData: nil,
            lineup: lineupForPrimaryShow,
            description: "A demo lineup stitched from the generated API schema while the live backend is offline.",
            address: "117 MacDougal St, New York, NY",
            room: "Main Room",
            imageUrl: stageImage,
            soldOut: false,
            distanceMiles: 2.1
        ),
        .init(
            id: 302,
            clubName: "The Stand",
            date: Date().addingTimeInterval(60 * 60 * 28),
            tickets: [.init(price: 24, purchaseUrl: nil, soldOut: false, _type: "Preferred seating")],
            name: "Atsuko Late Set",
            socialData: nil,
            lineup: [lineupForPrimaryShow[1]],
            description: "Demo fallback detail for a club-forward lineup.",
            address: "116 E 16th St, New York, NY",
            room: "Upstairs",
            imageUrl: altImage,
            soldOut: false,
            distanceMiles: 3.4
        )
    ]

    static let primaryShowDetail = showDetailResponse(id: 301) ?? Components.Schemas.ShowDetailResponse(data: showDetailData(for: 301), relatedShows: shows)
    static let primaryComedian = comedianDetail(id: 101) ?? Components.Schemas.ComedianDetail(id: 101, uuid: "demo-comedian-101", name: "Mark Normand", imageUrl: heroImage, socialData: primarySocial)
    static let primaryClub = clubDetail(id: 201) ?? Components.Schemas.ClubDetail(id: 201, name: "Comedy Cellar", imageUrl: clubImage, website: "https://www.comedycellar.com", address: "117 MacDougal St, New York, NY", zipCode: "10012", phoneNumber: "(212) 254-3480")

    static func comedians(matching query: String) -> [Components.Schemas.ComedianSearchItem] {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return comediansIndex }
        return comediansIndex.filter { $0.name.localizedCaseInsensitiveContains(trimmed) }
    }

    static func clubs(matching query: String) -> [Components.Schemas.ClubSearchItem] {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return clubIndex }
        return clubIndex.filter { ($0.name ?? "").localizedCaseInsensitiveContains(trimmed) }
    }

    static func comedianDetail(id: Int) -> Components.Schemas.ComedianDetail? {
        switch id {
        case 101:
            return .init(id: 101, uuid: "demo-comedian-101", name: "Mark Normand", imageUrl: heroImage, socialData: primarySocial)
        case 102:
            return .init(id: 102, uuid: "demo-comedian-102", name: "Atsuko Okatsuka", imageUrl: altImage, socialData: altSocial)
        case 103:
            return .init(id: 103, uuid: "demo-comedian-103", name: "Sam Morril", imageUrl: thirdImage, socialData: thirdSocial)
        default:
            return nil
        }
    }

    static func clubDetail(id: Int) -> Components.Schemas.ClubDetail? {
        switch id {
        case 201:
            return .init(id: 201, name: "Comedy Cellar", imageUrl: clubImage, website: "https://www.comedycellar.com", address: "117 MacDougal St, New York, NY", zipCode: "10012", phoneNumber: "(212) 254-3480")
        case 202:
            return .init(id: 202, name: "The Stand", imageUrl: clubAltImage, website: "https://thestandnyc.com", address: "116 E 16th St, New York, NY", zipCode: "10003", phoneNumber: "(212) 677-2600")
        default:
            return nil
        }
    }

    static func showDetailResponse(id: Int) -> Components.Schemas.ShowDetailResponse? {
        switch id {
        case 301:
            return .init(data: showDetailData(for: 301), relatedShows: [shows[1]])
        case 302:
            return .init(data: showDetailData(for: 302), relatedShows: [shows[0]])
        default:
            return nil
        }
    }

    private static func showDetailData(for id: Int) -> Components.Schemas.ShowDetail {
        switch id {
        case 301:
            return .init(
                id: 301,
                clubName: "Comedy Cellar",
                date: Date().addingTimeInterval(60 * 60 * 24),
                tickets: [.init(price: 30, purchaseUrl: "https://laughtrack.app/demo/tickets/301", soldOut: false, _type: "General admission")],
                name: "Mark Normand and Friends",
                socialData: nil,
                lineup: lineupForPrimaryShow,
                description: "A native detail presentation for the generated show contract, including CTA fallback and lineup favorites.",
                address: "117 MacDougal St, New York, NY",
                room: "Main Room",
                imageUrl: stageImage,
                soldOut: false,
                distanceMiles: 2.1,
                timezone: "America/New_York",
                showPageUrl: "https://laughtrack.app/demo/shows/301",
                club: .init(id: 201, name: "Comedy Cellar", address: "117 MacDougal St, New York, NY", imageUrl: clubImage, timezone: "America/New_York"),
                cta: .init(url: "https://laughtrack.app/demo/tickets/301", label: "Buy tickets", isSoldOut: false)
            )
        default:
            return .init(
                id: 302,
                clubName: "The Stand",
                date: Date().addingTimeInterval(60 * 60 * 28),
                tickets: [.init(price: 24, purchaseUrl: nil, soldOut: false, _type: "Preferred seating")],
                name: "Atsuko Late Set",
                socialData: nil,
                lineup: [lineupForPrimaryShow[1]],
                description: "The CTA falls back to the show page when a direct purchase link is missing.",
                address: "116 E 16th St, New York, NY",
                room: "Upstairs",
                imageUrl: altImage,
                soldOut: false,
                distanceMiles: 3.4,
                timezone: "America/New_York",
                showPageUrl: "https://laughtrack.app/demo/shows/302",
                club: .init(id: 202, name: "The Stand", address: "116 E 16th St, New York, NY", imageUrl: clubAltImage, timezone: "America/New_York"),
                cta: .init(url: nil, label: "Open show page", isSoldOut: false)
            )
        }
    }

    private static let lineupForPrimaryShow: [Components.Schemas.ComedianLineup] = [
        .init(name: "Mark Normand", imageUrl: heroImage, uuid: "demo-comedian-101", id: 101, userId: nil, socialData: primarySocial, isFavorite: false, showCount: 12),
        .init(name: "Atsuko Okatsuka", imageUrl: altImage, uuid: "demo-comedian-102", id: 102, userId: nil, socialData: altSocial, isFavorite: true, showCount: 8),
        .init(name: "Sam Morril", imageUrl: thirdImage, uuid: "demo-comedian-103", id: 103, userId: nil, socialData: thirdSocial, isFavorite: false, showCount: 6)
    ]

    private static let heroImage = "https://images.unsplash.com/photo-1516280440614-37939bbacd81?auto=format&fit=crop&w=1200&q=80"
    private static let altImage = "https://images.unsplash.com/photo-1509824227185-9c5a01ceba0d?auto=format&fit=crop&w=1200&q=80"
    private static let thirdImage = "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?auto=format&fit=crop&w=1200&q=80"
    private static let stageImage = "https://images.unsplash.com/photo-1503095396549-807759245b35?auto=format&fit=crop&w=1200&q=80"
    private static let clubImage = "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1200&q=80"
    private static let clubAltImage = "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?auto=format&fit=crop&w=1200&q=80"
}

private extension String {
    var nonEmpty: String? {
        isEmpty ? nil : self
    }

    func socialURL(host: String) -> URL? {
        guard !isEmpty else { return nil }
        return URL(string: "https://\(host)\(self.hasPrefix("@") ? String(self.dropFirst()) : self)")
    }
}

private extension URL {
    static func normalizedExternalURL(_ rawValue: String?) -> URL? {
        guard let rawValue, !rawValue.isEmpty else { return nil }
        if let direct = URL(string: rawValue), direct.scheme != nil {
            return direct
        }
        return URL(string: "https://\(rawValue)")
    }
}
