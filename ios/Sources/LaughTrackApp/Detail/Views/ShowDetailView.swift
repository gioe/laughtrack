import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ShowDetailView: View {
    let showID: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL

    @StateObject private var model: ShowDetailModel
    @State private var feedbackMessage: String?

    init(showID: Int, apiClient: Client) {
        self.showID = showID
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: ShowDetailModel(showID: showID))
    }

    var body: some View {
        ScrollView {
            switch model.phase {
            case .idle, .loading:
                LoadingCard()
                    .padding()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.reload(apiClient: apiClient, favorites: favorites) },
                    signIn: { coordinator.push(.profile) }
                )
                .padding()
            case .success(let response):
                let show = response.data
                VStack(alignment: .leading, spacing: 0) {
                    DetailHero(
                        title: show.name ?? "Untitled show",
                        subtitle: ShowFormatting.detailDate(show.date, timezoneID: show.timezone),
                        imageURL: show.imageUrl,
                        badges: ShowDetailPresentation.heroBadges(for: show)
                    )
                    .ignoresSafeArea(.container, edges: .top)

                    VStack(alignment: .leading, spacing: 20) {
                        ShowSummarySection(show: show) {
                            coordinator.open(.club(show.club.id))
                        }

                        if
                            ShowDetailPresentation.shouldShowEditorNote(for: show),
                            let description = show.description,
                            !description.isEmpty
                        {
                            DetailTextCard(eyebrow: "Editor’s note", title: "About this show", text: description)
                        }

                        ShowCTASection(show: show) { url in
                            openURL(url)
                        }

                        ShowLineupSection(
                            lineup: show.lineup ?? [],
                            apiClient: apiClient,
                            feedbackMessage: $feedbackMessage
                        ) { comedian in
                            coordinator.open(.comedian(comedian.id))
                        }

                        RelatedShowsSection(relatedShows: response.relatedShows) { related in
                            coordinator.open(.show(related.id))
                        }
                    }
                    .padding()
                }
            }
        }
        .ignoresSafeArea(.container, edges: .top)
        .accessibilityIdentifier(LaughTrackViewTestID.showDetailScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .modifier(EntityDetailNavigationChrome(entity: .show))
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

}

struct ShowDetailFact: Equatable {
    let label: String
    let value: String
}

enum ShowDetailPresentation {
    static func heroBadges(for show: Components.Schemas.ShowDetail) -> [DetailHeroBadge] {
        []
    }

    static func summaryFacts(for show: Components.Schemas.ShowDetail) -> [ShowDetailFact] {
        [
            ShowDetailFact(
                label: "When",
                value: ShowFormatting.listDate(show.date, timezoneID: show.timezone)
            ),
            ShowDetailFact(label: "Tickets", value: ticketSummary(for: show)),
            ShowDetailFact(label: "Venue", value: show.club.name),
            optionalFact(label: "Room", value: show.room),
            optionalFact(label: "Distance", value: ShowFormatting.distance(show.distanceMiles)),
            optionalFact(label: "Address", value: show.address ?? show.club.address)
        ]
        .compactMap { $0 }
    }

    static func ticketSubtitle(for show: Components.Schemas.ShowDetail) -> String {
        if show.cta.isSoldOut {
            return "This show is marked sold out, but the venue path stays visible."
        }

        if show.tickets?.isEmpty == false {
            return "Choose a ticket option or open the venue checkout."
        }

        return "Open the venue checkout when a ticket link is available."
    }

    static func shouldShowEditorNote(for show: Components.Schemas.ShowDetail) -> Bool {
        false
    }

    private static func optionalFact(label: String, value: String?) -> ShowDetailFact? {
        guard let value, !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return nil
        }
        return ShowDetailFact(label: label, value: value)
    }

    private static func ticketSummary(for show: Components.Schemas.ShowDetail) -> String {
        if show.cta.isSoldOut || show.soldOut == true {
            return "Sold out"
        }

        let prices = (show.tickets ?? []).compactMap(\.price)
        guard let lowest = prices.min() else {
            return "Unavailable"
        }

        if lowest <= 0 {
            return "Free"
        }

        return currencyFormatter.string(from: NSNumber(value: lowest)) ?? "$\(lowest)"
    }

    private static let currencyFormatter: NumberFormatter = {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.locale = Locale(identifier: "en_US")
        formatter.currencyCode = "USD"
        return formatter
    }()
}

private struct ShowSummarySection: View {
    let show: Components.Schemas.ShowDetail
    let openClub: () -> Void

    private let columns = [
        GridItem(.flexible(), spacing: 10),
        GridItem(.flexible(), spacing: 10)
    ]

    var body: some View {
        let facts = ShowDetailPresentation.summaryFacts(for: show)

        LaughTrackCard {
            VStack(alignment: .leading, spacing: 14) {
                LaughTrackSectionHeader(
                    eyebrow: "Show details",
                    title: "Plan your night"
                )

                LazyVGrid(columns: columns, alignment: .leading, spacing: 10) {
                    ForEach(facts, id: \.label) { fact in
                        ShowSummaryFactTile(fact: fact)
                    }
                }

                LaughTrackButton(
                    "Open venue",
                    systemImage: "building.2.fill",
                    tone: .tertiary
                ) {
                    openClub()
                }
            }
        }
    }
}

private struct ShowSummaryFactTile: View {
    @Environment(\.appTheme) private var theme

    let fact: ShowDetailFact

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: 4) {
            Text(fact.label)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.accentStrong)
                .textCase(.uppercase)
            Text(fact.value)
                .font(laughTrack.typography.body.weight(.semibold))
                .foregroundStyle(laughTrack.colors.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(10)
        .frame(maxWidth: .infinity, minHeight: 72, alignment: .topLeading)
        .background(laughTrack.colors.surfaceMuted)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
    }
}

private struct ShowLineupSection: View {
    let lineup: [Components.Schemas.ComedianLineup]
    let apiClient: Client
    @Binding var feedbackMessage: String?
    let openDetail: (Components.Schemas.ComedianLineup) -> Void

    var body: some View {
        LaughTrackCard {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(
                    eyebrow: "Lineup",
                    title: "Tonight’s bill",
                    subtitle: "Tap a comic to see their upcoming shows."
                )

                if lineup.isEmpty {
                    EmptyCard(message: "Lineup details are not available yet.")
                } else {
                    ForEach(lineup, id: \.uuid) { comedian in
                        ComedianLineupRow(
                            comedian: comedian,
                            apiClient: apiClient,
                            feedbackMessage: $feedbackMessage,
                            openDetail: { openDetail(comedian) }
                        )
                    }
                }
            }
        }
    }
}

private struct RelatedShowsSection: View {
    let relatedShows: [Components.Schemas.Show]
    let openDetail: (Components.Schemas.Show) -> Void

    var body: some View {
        LaughTrackCard(tone: .muted) {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(
                    eyebrow: "Keep browsing",
                    title: "Related shows",
                    subtitle: "More shows you might like."
                )

                if relatedShows.isEmpty {
                    EmptyCard(message: "No related shows are available yet.")
                } else {
                    ForEach(relatedShows, id: \.id) { related in
                        Button {
                            openDetail(related)
                        } label: {
                            ShowRow(show: related)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
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

        LaughTrackCard(tone: .standard) {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(
                    eyebrow: "Tickets",
                    title: show.cta.isSoldOut ? "Join the wait for the next one" : "Secure your seat",
                    subtitle: ShowDetailPresentation.ticketSubtitle(for: show)
                )

                if let primaryURL {
                    LaughTrackButton(
                        show.cta.label,
                        systemImage: "arrow.up.right",
                        tone: show.cta.isSoldOut ? .secondary : .primary
                    ) {
                        openURL(primaryURL)
                    }
                    .disabled(show.cta.isSoldOut)
                } else {
                    EmptyCard(message: "Tickets are not linked yet for this show.")
                }

                if let fallbackURL, primaryURL != fallbackURL {
                    LaughTrackButton("Open show page", systemImage: "safari", tone: .tertiary) {
                        openURL(fallbackURL)
                    }
                }

                if let tickets = show.tickets, !tickets.isEmpty {
                    VStack(spacing: 10) {
                        ForEach(Array(tickets.enumerated()), id: \.offset) { index, ticket in
                            HStack(spacing: 12) {
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
                                    LaughTrackButton(
                                        ticket.soldOut == true ? "Sold out" : "Open",
                                        systemImage: ticket.soldOut == true ? "xmark.circle" : "arrow.up.right",
                                        tone: ticket.soldOut == true ? .secondary : .tertiary,
                                        fullWidth: false
                                    ) {
                                        openURL(url)
                                    }
                                    .disabled(ticket.soldOut == true)
                                }
                            }
                            .padding(12)
                            .background(laughTrack.colors.surfaceMuted)
                            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                        }
                    }
                }
            }
        }
    }
}
