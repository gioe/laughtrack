import SwiftUI
import EventKit
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
    @StateObject private var calendarWriter = ShowCalendarWriter()
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
                        title: ShowTitlePresentation.title(for: show),
                        subtitle: ShowFormatting.detailDate(show.date, timezoneID: show.timezone),
                        imageURL: show.imageUrl,
                        badges: ShowDetailPresentation.heroBadges(for: show)
                    )
                    .ignoresSafeArea(.container, edges: .top)

                    VStack(alignment: .leading, spacing: 20) {
                        ShowSummarySection(show: show, openClub: {
                            coordinator.open(.club(show.club.id))
                        }, openTicketURL: { url in
                            openURL(url)
                        }, addToCalendar: {
                            Task {
                                feedbackMessage = await calendarWriter.add(show)
                            }
                        })

                        if
                            ShowDetailPresentation.shouldShowEditorNote(for: show),
                            let description = show.description,
                            !description.isEmpty
                        {
                            DetailTextCard(eyebrow: "Editor’s note", title: "About this show", text: description)
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
            optionalFact(label: "Distance", value: ShowFormatting.distance(show.distanceMiles))
        ]
        .compactMap { $0 }
    }

    static func primaryTicketURL(for show: Components.Schemas.ShowDetail) -> URL? {
        guard !show.cta.isSoldOut, show.soldOut != true else {
            return nil
        }

        let ticketURL = show.tickets?
            .first { $0.soldOut != true && URL.normalizedExternalURL($0.purchaseUrl) != nil }
            .flatMap { URL.normalizedExternalURL($0.purchaseUrl) }

        return ticketURL
            ?? URL.normalizedExternalURL(show.cta.url)
            ?? URL.normalizedExternalURL(show.showPageUrl)
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
    let openTicketURL: (URL) -> Void
    let addToCalendar: () -> Void

    private let columns = [
        GridItem(.flexible(), spacing: 10),
        GridItem(.flexible(), spacing: 10)
    ]

    var body: some View {
        let facts = ShowDetailPresentation.summaryFacts(for: show)
        let ticketURL = ShowDetailPresentation.primaryTicketURL(for: show)

        LaughTrackCard {
            VStack(alignment: .leading, spacing: 14) {
                LaughTrackSectionHeader(
                    eyebrow: "Show details",
                    title: "Plan your night"
                )

                LazyVGrid(columns: columns, alignment: .leading, spacing: 10) {
                    ForEach(facts, id: \.label) { fact in
                        if fact.label == "When" {
                            Button(action: addToCalendar) {
                                ShowSummaryFactTile(
                                    fact: fact,
                                    action: .init(systemImage: "calendar.badge.plus", label: "Add to calendar")
                                )
                            }
                            .buttonStyle(.plain)
                            .accessibilityHint("Adds this show to your phone calendar")
                        } else if fact.label == "Tickets", let ticketURL {
                            Button {
                                openTicketURL(ticketURL)
                            } label: {
                                ShowSummaryFactTile(
                                    fact: fact,
                                    action: .init(systemImage: "arrow.up.right", label: "Buy tickets")
                                )
                            }
                            .buttonStyle(.plain)
                            .accessibilityHint("Opens the ticket purchase page")
                        } else if fact.label == "Venue" {
                            Button(action: openClub) {
                                ShowSummaryFactTile(
                                    fact: fact,
                                    action: .init(systemImage: "building.2.fill", label: "Open venue")
                                )
                            }
                            .buttonStyle(.plain)
                            .accessibilityHint("Opens the venue detail page")
                        } else {
                            ShowSummaryFactTile(fact: fact)
                        }
                    }
                }
            }
        }
    }
}

private struct ShowSummaryFactTile: View {
    struct ActionAffordance {
        let systemImage: String
        let label: String
    }

    @Environment(\.appTheme) private var theme

    let fact: ShowDetailFact
    var action: ActionAffordance?

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let isActionable = action != nil

        VStack(alignment: .leading, spacing: 4) {
            Text(fact.label)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.accentStrong)
                .textCase(.uppercase)
            Text(fact.value)
                .font(laughTrack.typography.body.weight(.semibold))
                .foregroundStyle(laughTrack.colors.textPrimary)
                .fixedSize(horizontal: false, vertical: true)

            if let action {
                HStack(spacing: 6) {
                    Image(systemName: action.systemImage)
                        .font(.system(size: 13, weight: .semibold))
                    Text(action.label)
                        .font(laughTrack.typography.metadata.weight(.semibold))
                    Image(systemName: "arrow.right")
                        .font(.system(size: 12, weight: .bold))
                }
                .foregroundStyle(laughTrack.colors.accentStrong)
                .padding(.top, 4)
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, minHeight: 72, alignment: .topLeading)
        .background(isActionable ? laughTrack.colors.surfaceElevated : laughTrack.colors.surfaceMuted)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(isActionable ? laughTrack.colors.accentStrong.opacity(0.45) : laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .shadow(color: isActionable ? .black.opacity(0.08) : .clear, radius: 10, x: 0, y: 5)
    }
}

struct ShowCalendarEventPresentation: Equatable {
    let title: String
    let startDate: Date
    let endDate: Date
    let location: String?
    let notes: String
    let url: URL?

    static func event(for show: Components.Schemas.ShowDetail) -> ShowCalendarEventPresentation {
        let title = ShowTitlePresentation.title(for: show)
        let location = [show.club.name as String?, show.address ?? show.club.address]
            .compactMap { value in
                guard let value else { return nil }
                let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
                return trimmed.isEmpty ? nil : trimmed
            }
            .joined(separator: "\n")
        let url = ShowDetailPresentation.primaryTicketURL(for: show)
            ?? URL.normalizedExternalURL(show.showPageUrl)

        return ShowCalendarEventPresentation(
            title: title,
            startDate: show.date,
            endDate: show.date.addingTimeInterval(2 * 60 * 60),
            location: location.isEmpty ? nil : location,
            notes: "Added from LaughTrack.",
            url: url
        )
    }
}

@MainActor
private final class ShowCalendarWriter: ObservableObject {
    private let eventStore = EKEventStore()

    func add(_ show: Components.Schemas.ShowDetail) async -> String {
        do {
            let granted = try await requestCalendarAccess()
            guard granted else {
                return "Calendar access is needed to add this show."
            }

            let presentation = ShowCalendarEventPresentation.event(for: show)
            guard let calendar = eventStore.defaultCalendarForNewEvents else {
                return "No writable calendar is available on this device."
            }

            let event = EKEvent(eventStore: eventStore)
            event.title = presentation.title
            event.startDate = presentation.startDate
            event.endDate = presentation.endDate
            event.location = presentation.location
            event.notes = presentation.notes
            event.url = presentation.url
            event.calendar = calendar

            try eventStore.save(event, span: .thisEvent)
            return "Added \(presentation.title) to Calendar."
        } catch {
            return "Could not add this show to Calendar."
        }
    }

    private func requestCalendarAccess() async throws -> Bool {
        try await withCheckedThrowingContinuation { continuation in
            if #available(iOS 17.0, macOS 14.0, *) {
                eventStore.requestWriteOnlyAccessToEvents { granted, error in
                    if let error {
                        continuation.resume(throwing: error)
                    } else {
                        continuation.resume(returning: granted)
                    }
                }
            } else {
                eventStore.requestAccess(to: .event) { granted, error in
                    if let error {
                        continuation.resume(throwing: error)
                    } else {
                        continuation.resume(returning: granted)
                    }
                }
            }
        }
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
