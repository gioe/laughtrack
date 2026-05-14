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
    @State private var safariURL: URL?

    init(showID: Int, apiClient: Client) {
        self.showID = showID
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: ShowDetailModel(showID: showID))
    }

    private var navigationTitle: String {
        if case .success(let response) = model.phase {
            return ShowTitlePresentation.title(for: response.data)
        }
        return ""
    }

    var body: some View {
        Group {
            switch model.phase {
            case .idle, .loading:
                ShowDetailSkeleton()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.reload(apiClient: apiClient, favorites: favorites) },
                    signIn: { coordinator.push(.profile) }
                )
                .padding()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .success(let response):
                let show = response.data
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        DetailHero(
                            title: nil,
                            subtitle: nil,
                            imageURL: show.imageUrl,
                            badges: ShowDetailPresentation.heroBadges(for: show)
                        )
                        .ignoresSafeArea(.container, edges: .top)

                        VStack(alignment: .leading, spacing: 20) {
                            ShowSummarySection(show: show, openClub: {
                                coordinator.open(.club(show.club.id))
                            }, openTicketURL: { url in
                                ExternalLinkRouter.route(url, presentedURL: $safariURL, openURL: openURL)
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
                        .padding(.horizontal, 8)
                        .padding(.vertical, theme.spacing.lg)
                    }
                }
                .safariSheet(url: $safariURL)
            }
        }
        .accessibilityIdentifier(LaughTrackViewTestID.showDetailScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .modifier(EntityDetailNavigationChrome(entity: .show, title: navigationTitle))
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
        let countdown = ShowFormatting.countdown(for: show.date)
        return [
            DetailHeroBadge(
                title: countdown.label,
                systemImage: countdownSymbol(countdown.tone),
                tone: countdownBadgeTone(countdown.tone)
            )
        ]
    }

    private static func countdownSymbol(_ tone: ShowFormatting.ShowCountdownTone) -> String {
        switch tone {
        case .future: return "clock"
        case .live: return "dot.radiowaves.left.and.right"
        case .past: return "clock.arrow.circlepath"
        }
    }

    private static func countdownBadgeTone(_ tone: ShowFormatting.ShowCountdownTone) -> LaughTrackBadgeTone {
        switch tone {
        case .future: return .accent
        case .live: return .highlight
        case .past: return .neutral
        }
    }

    static func summaryFacts(for show: Components.Schemas.ShowDetail) -> [ShowDetailFact] {
        [
            ShowDetailFact(
                label: "When",
                value: ShowFormatting.listDate(show.date, timezoneID: show.timezone)
            ),
            ShowDetailFact(label: "Venue", value: show.club.name),
            optionalFact(label: "Distance", value: ShowFormatting.distance(show.distanceMiles)),
            ShowDetailFact(label: "Tickets", value: ticketSummary(for: show))
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

    var body: some View {
        let facts = ShowDetailPresentation.summaryFacts(for: show)
        let ticketURL = ShowDetailPresentation.primaryTicketURL(for: show)

        LaughTrackCard(density: .tight) {
            VStack(spacing: 0) {
                ForEach(Array(facts.enumerated()), id: \.element.label) { index, fact in
                    Group {
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

                    if index < facts.count - 1 {
                        Divider()
                            .padding(.leading, 50)
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

        HStack(spacing: 14) {
            ZStack {
                Circle()
                    .fill(laughTrack.colors.surfaceMuted)
                Image(systemName: leadingSymbol)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
            .frame(width: 36, height: 36)

            VStack(alignment: .leading, spacing: 2) {
                Text(fact.label)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .textCase(.uppercase)
                Text(fact.value)
                    .font(laughTrack.typography.body.weight(.semibold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            if isActionable {
                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.textSecondary)
            }
        }
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .contentShape(Rectangle())
    }

    private var leadingSymbol: String {
        switch fact.label {
        case "When": return "calendar"
        case "Tickets": return "ticket.fill"
        case "Venue": return "building.2.fill"
        default: return "info.circle"
        }
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
        LaughTrackCard(density: .tight) {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(title: "Lineup")

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
        LaughTrackCard(tone: .muted, density: .tight) {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(
                    title: "Can’t Make It?",
                    subtitle: "Here are some more shows you might like"
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
