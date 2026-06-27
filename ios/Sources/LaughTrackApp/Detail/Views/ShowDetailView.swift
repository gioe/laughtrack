import SwiftUI
import EventKit
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
#if canImport(UIKit)
import UIKit
#endif

struct ShowDetailView: View {
    let showID: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @EnvironmentObject private var softPushPromptCoordinator: SoftPushPromptCoordinator
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
                let isOpenMic = ShowDetailPresentation.isOpenMic(show)
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        MarqueeHero(
                            title: ShowTitlePresentation.title(for: show),
                            eyebrow: show.club.name,
                            imageURL: ShowDetailPresentation.heroImageURL(for: show),
                            thumbnailStyle: ShowDetailPresentation.heroThumbnailStyle(for: show),
                            badges: ShowDetailPresentation.heroBadges(for: show),
                            fallbackSystemImage: "ticket.fill"
                        )

                        if authManager.currentUser?.isAdmin == true {
                            AdminShowIDBadge(showID: show.id)
                                .padding(.horizontal, 8)
                                .padding(.top, theme.spacing.sm)
                        }

                        VStack(alignment: .leading, spacing: 20) {
                            ShowSummarySection(show: show, isOpenMic: isOpenMic, openClub: {
                                coordinator.open(.club(show.club.id))
                            }, openTicketURL: { url in
                                Task {
                                    let recorder = ShowDetailTicketClickRecorder(apiClient: apiClient)
                                    _ = await recorder.record(
                                        showID: show.id,
                                        clubID: show.club.id,
                                        destinationURL: url
                                    )
                                    ExternalLinkRouter.route(url, presentedURL: $safariURL, openURL: openURL)
                                }
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

                            if !isOpenMic, let lineup = show.lineup, !lineup.isEmpty {
                                ShowLineupSection(lineup: lineup) { comedian in
                                    coordinator.open(.comedian(comedian.id))
                                }
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
        .ignoresSafeArea(.container, edges: .top)
        .accessibilityIdentifier(LaughTrackViewTestID.showDetailScreen)
        .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
        .overlay(alignment: .top) {
            DetailChromeBar(
                onBack: { coordinator.pop() },
                onHome: coordinator.detailHomeAction,
                favoriteState: nil
            )
        }
        .modifier(EntityDetailNavigationChrome(entity: .show, title: navigationTitle))
        .task {
            await model.loadIfNeeded(apiClient: apiClient, favorites: favorites)
        }
        .task(id: showID) {
            // Show-detail open counts as an engagement signal for the push
            // permission cadence. Debounced inside SoftPushPromptCoordinator
            // by showID so back-stack revisits of the same show don't burn
            // a second signal; .task(id:) restarts when navigating between
            // distinct shows so each new show ID reaches the coordinator.
            let isPostOnboarding = authManager.currentUser?.comedianOnboardingCompleted == true
            await softPushPromptCoordinator.handleShowDetailViewed(
                showID: showID,
                isPostOnboarding: isPostOnboarding
            )
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

struct ShowDetailTicketClickRecorder {
    let apiClient: Client

    func record(showID: Int, clubID: Int, destinationURL: URL) async -> Bool {
        do {
            let output = try await apiClient.recordTicketClick(
                .init(
                    body: .json(
                        .init(
                            showId: showID,
                            clubId: clubID,
                            destinationUrl: destinationURL.absoluteString,
                            sourceSurface: .iosShowDetail
                        )
                    )
                )
            )
            if case .created = output {
                return true
            }
        } catch {
            return false
        }
        return false
    }
}

struct ShowDetailFact: Equatable {
    let label: String
    let value: String
}

enum ShowDetailPresentation {
    static func heroBadges(for _: Components.Schemas.ShowDetail) -> [DetailHeroBadge] {
        []
    }

    static func summaryFacts(for show: Components.Schemas.ShowDetail) -> [ShowDetailFact] {
        let isOpenMic = isOpenMic(show)
        return [
            ShowDetailFact(
                label: "When",
                value: ShowFormatting.listDate(show.date, timezoneID: show.timezone)
            ),
            ShowDetailFact(label: "Venue", value: show.club.name),
            optionalFact(label: "Distance", value: ShowFormatting.distance(show.distanceMiles)),
            ShowDetailFact(
                label: "Tickets",
                value: isOpenMic ? "RSVP" : ShowPricePresentation.detailTicketSummary(for: show)
            )
        ]
        .compactMap { $0 }
    }

    /// Tag-based open-mic detection mirrors `ShowRow.isOpenMic` so row + detail
    /// surfaces share a single signal. Falls back to the title heuristic for
    /// shows whose tag list hasn't been backfilled yet.
    static func isOpenMic(_ show: Components.Schemas.ShowDetail) -> Bool {
        if ShowFormatting.isOpenMic(tags: show.tags) { return true }
        return ShowFormatting.isOpenMic(show.name)
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

    /// The lineup item we treat as the headliner. The API has no role field on
    /// lineup, so we approximate: highest `socialData.popularity`, breaking
    /// ties by `showCount` then list position. Returns nil for empty lineups
    /// and open mics.
    static func headliner(in show: Components.Schemas.ShowDetail) -> Components.Schemas.ComedianLineup? {
        guard !isOpenMic(show), let lineup = show.lineup, !lineup.isEmpty else {
            return nil
        }
        return lineup.enumerated().sorted { lhs, rhs in
            let lhsPop = lhs.element.socialData?.popularity ?? -1
            let rhsPop = rhs.element.socialData?.popularity ?? -1
            if lhsPop != rhsPop { return lhsPop > rhsPop }
            let lhsCount = lhs.element.showCount ?? 0
            let rhsCount = rhs.element.showCount ?? 0
            if lhsCount != rhsCount { return lhsCount > rhsCount }
            return lhs.offset < rhs.offset
        }.first?.element
    }

    /// Hero image URL: prefer the inferred headliner's headshot when present,
    /// fall back to the show's own image (venue photo / show poster) otherwise.
    static func heroImageURL(for show: Components.Schemas.ShowDetail) -> String {
        if
            let headshot = headliner(in: show)?.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines),
            !headshot.isEmpty
        {
            return headshot
        }
        let clubImage = show.club.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        if !clubImage.isEmpty {
            return clubImage
        }
        return show.imageUrl
    }

    static func heroThumbnailStyle(for show: Components.Schemas.ShowDetail) -> MarqueeHeroThumbnailStyle {
        if
            let headliner = headliner(in: show),
            !headliner.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        {
            return .framedComedian(caption: headliner.name)
        }
        return .clubMarquee
    }

    private static func optionalFact(label: String, value: String?) -> ShowDetailFact? {
        guard let value, !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return nil
        }
        return ShowDetailFact(label: label, value: value)
    }

}

private struct ShowSummarySection: View {
    let show: Components.Schemas.ShowDetail
    let isOpenMic: Bool
    let openClub: () -> Void
    let openTicketURL: (URL) -> Void
    let addToCalendar: () -> Void

    @State private var perforationY: CGFloat = 0

    var body: some View {
        let facts = ShowDetailPresentation.summaryFacts(for: show)
        let ticketURL = ShowDetailPresentation.primaryTicketURL(for: show)
        // The perforation replaces the divider BEFORE the last fact row
        // (Tickets), turning that row into the ticket's stub.
        let perforationIndex = facts.count - 2
        let shape = TicketShape(perforationY: perforationY)

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
                    } else if fact.label == "Tickets" {
                        let infoMessage = isOpenMic
                            ? nil
                            : (ShowPricePresentation.detailTicketPriceUnavailable(fact.value)
                                ? ShowPricePresentation.priceUnavailableExplanation
                                : nil)
                        let ctaLabel = isOpenMic ? "RSVP" : "Buy tickets"
                        let ctaHint = isOpenMic
                            ? "Opens the RSVP page"
                            : "Opens the ticket purchase page"
                        if let ticketURL {
                            Button {
                                openTicketURL(ticketURL)
                            } label: {
                                ShowSummaryFactTile(
                                    fact: fact,
                                    action: .init(
                                        systemImage: "arrow.up.right",
                                        label: ctaLabel,
                                        style: .pill
                                    ),
                                    infoMessage: infoMessage
                                )
                            }
                            .buttonStyle(.plain)
                            .accessibilityHint(ctaHint)
                        } else {
                            ShowSummaryFactTile(fact: fact, infoMessage: infoMessage)
                        }
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
                    if index == perforationIndex {
                        TicketPerforation()
                            .background(
                                GeometryReader { geo in
                                    Color.clear.preference(
                                        key: PerforationYPreferenceKey.self,
                                        value: geo.frame(in: .named("ticket")).midY
                                    )
                                }
                            )
                    } else {
                        Rectangle()
                            .fill(TicketTheme.inkMuted.opacity(0.22))
                            .frame(height: 1)
                            .padding(.leading, 50)
                    }
                }
            }

        }
        .padding(8)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(TicketTheme.paper)
        .clipShape(shape)
        .overlay {
            shape.stroke(TicketTheme.inkBorder.opacity(0.45), lineWidth: 1)
        }
        .coordinateSpace(name: "ticket")
        .onPreferenceChange(PerforationYPreferenceKey.self) { perforationY = $0 }
    }
}

/// Warm paper-and-ink palette used inside the show-summary ticket card. Kept
/// local to the show-detail file because it intentionally diverges from the
/// surrounding dark-themed canvas.
enum TicketTheme {
    static let paper = Color(red: 0.93, green: 0.87, blue: 0.74)
    static let paperShade = Color(red: 0.85, green: 0.77, blue: 0.62)
    static let ink = Color(red: 0.13, green: 0.09, blue: 0.04)
    static let inkMuted = Color(red: 0.42, green: 0.32, blue: 0.20)
    static let inkBorder = Color(red: 0.55, green: 0.44, blue: 0.30)
}


/// Rounded-rectangle card silhouette with two semicircular notches carved into
/// the left and right edges at `perforationY`. Combined with a dashed line
/// between the notches it reads as a paper ticket with a tear stub.
private struct TicketShape: Shape {
    let perforationY: CGFloat
    var notchRadius: CGFloat = 9
    var cornerRadius: CGFloat = 18

    func path(in rect: CGRect) -> Path {
        let w = rect.width
        let h = rect.height
        let r = min(cornerRadius, min(w, h) / 2)
        let py = perforationY
        let nr = notchRadius

        // While we wait for the perforationY preference to settle, fall back
        // to a regular rounded rect so the very first frame doesn't render
        // half-drawn.
        guard py > r + nr, py < h - r - nr else {
            return Path(roundedRect: rect, cornerRadius: r, style: .continuous)
        }

        var path = Path()
        // top edge, starting after top-left corner radius
        path.move(to: CGPoint(x: r, y: 0))
        path.addLine(to: CGPoint(x: w - r, y: 0))
        // top-right corner
        path.addArc(center: CGPoint(x: w - r, y: r), radius: r,
                    startAngle: .degrees(-90), endAngle: .degrees(0), clockwise: false)
        // right edge down to top of right notch
        path.addLine(to: CGPoint(x: w, y: py - nr))
        // right notch — semicircle bulging into the card
        path.addArc(center: CGPoint(x: w, y: py), radius: nr,
                    startAngle: .degrees(-90), endAngle: .degrees(90), clockwise: true)
        // right edge to bottom-right corner
        path.addLine(to: CGPoint(x: w, y: h - r))
        // bottom-right corner
        path.addArc(center: CGPoint(x: w - r, y: h - r), radius: r,
                    startAngle: .degrees(0), endAngle: .degrees(90), clockwise: false)
        // bottom edge
        path.addLine(to: CGPoint(x: r, y: h))
        // bottom-left corner
        path.addArc(center: CGPoint(x: r, y: h - r), radius: r,
                    startAngle: .degrees(90), endAngle: .degrees(180), clockwise: false)
        // left edge up to bottom of left notch
        path.addLine(to: CGPoint(x: 0, y: py + nr))
        // left notch — semicircle bulging into the card
        path.addArc(center: CGPoint(x: 0, y: py), radius: nr,
                    startAngle: .degrees(90), endAngle: .degrees(-90), clockwise: true)
        // left edge up to top-left corner
        path.addLine(to: CGPoint(x: 0, y: r))
        // top-left corner
        path.addArc(center: CGPoint(x: r, y: r), radius: r,
                    startAngle: .degrees(180), endAngle: .degrees(-90), clockwise: false)
        path.closeSubpath()
        return path
    }
}

private struct PerforationYPreferenceKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        let next = nextValue()
        if next > 0 { value = next }
    }
}

private struct TicketPerforation: View {
    var body: some View {
        GeometryReader { geo in
            Path { path in
                let y = geo.size.height / 2
                path.move(to: CGPoint(x: 14, y: y))
                path.addLine(to: CGPoint(x: geo.size.width - 14, y: y))
            }
            .stroke(
                TicketTheme.inkMuted.opacity(0.55),
                style: StrokeStyle(lineWidth: 1, dash: [4, 4])
            )
        }
        .frame(height: 18)
    }
}

private struct ShowSummaryFactTile: View {
    struct ActionAffordance {
        let systemImage: String
        let label: String
        var style: Style = .chevron

        enum Style {
            case chevron
            case pill
        }
    }

    @Environment(\.appTheme) private var theme

    let fact: ShowDetailFact
    var action: ActionAffordance?
    var infoMessage: String?

    @State private var showingInfo = false

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: 14) {
            ZStack {
                Circle()
                    .fill(TicketTheme.paperShade)
                Image(systemName: leadingSymbol)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
            .frame(width: 36, height: 36)

            VStack(alignment: .leading, spacing: 2) {
                Text(fact.label)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(TicketTheme.inkMuted)
                    .textCase(.uppercase)
                HStack(spacing: 6) {
                    Text(fact.value)
                        .font(.system(.body, design: .monospaced).weight(.semibold))
                        .foregroundStyle(TicketTheme.ink)
                        .fixedSize(horizontal: false, vertical: true)
                    if infoMessage != nil {
                        Button {
                            showingInfo = true
                        } label: {
                            Image(systemName: "info.circle")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(TicketTheme.inkMuted)
                                .padding(4)
                                .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("More information")
                        .accessibilityHint("Shows why this value is unavailable")
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            if let action {
                switch action.style {
                case .chevron:
                    Image(systemName: "chevron.right")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(TicketTheme.inkMuted)
                case .pill:
                    HStack(spacing: 5) {
                        Text(action.label.uppercased())
                            .font(.system(size: 11, weight: .heavy, design: .rounded))
                            .tracking(0.6)
                        Image(systemName: action.systemImage)
                            .font(.system(size: 10, weight: .bold))
                    }
                    .foregroundStyle(Color.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(laughTrack.colors.accentStrong)
                    .clipShape(Capsule())
                    .shadow(color: laughTrack.colors.accentStrong.opacity(0.4), radius: 6, y: 2)
                }
            }
        }
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .contentShape(Rectangle())
        .alert(fact.label, isPresented: $showingInfo) {
            Button("OK", role: .cancel) { }
        } message: {
            if let infoMessage {
                Text(infoMessage)
            }
        }
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
    let openDetail: (Components.Schemas.ComedianLineup) -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        LaughTrackCard(density: .tight) {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(eyebrow: "On the bill", title: "Lineup")

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(alignment: .top, spacing: theme.spacing.md) {
                        ForEach(lineup, id: \.uuid) { comedian in
                            Button {
                                openDetail(comedian)
                            } label: {
                                ComedianLineupTile(comedian: comedian)
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel(comedian.name)
                        }
                    }
                    .padding(.horizontal, 4)
                    .padding(.vertical, 2)
                }
            }
        }
    }
}

/// Pure derivation of the role badge shown on a comedian lineup tile in show
/// detail. Returns the trimmed, non-empty role string (the view renders it
/// uppercased) or nil when the lineup item carries no role. Extracted so the
/// badge logic is verifiable without hosting the view — HostedView's
/// accessibility-tree wiring is broken on iOS 26.x / 18.6 simulators
/// (TASK-2535).
enum ShowLineupPresentation {
    static func roleBadge(for comedian: Components.Schemas.ComedianLineup) -> String? {
        guard
            let role = comedian.role?.trimmingCharacters(in: .whitespacesAndNewlines),
            !role.isEmpty
        else {
            return nil
        }
        return role
    }
}

private struct ComedianLineupTile: View {
    let comedian: Components.Schemas.ComedianLineup

    @Environment(\.appTheme) private var theme

    private static let tileWidth: CGFloat = 96
    private static let posterSize: CGFloat = 80
    private static let posterFrameInset: CGFloat = 6

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(spacing: 8) {
            ZStack {
                photo
                    .frame(width: Self.posterSize, height: Self.posterSize)
                    .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 6, style: .continuous)
                            .stroke(Color.black.opacity(0.55), lineWidth: 1)
                    )

                RoundedRectangle(cornerRadius: 9, style: .continuous)
                    .strokeBorder(
                        laughTrack.colors.accentStrong,
                        style: StrokeStyle(
                            lineWidth: 1.8,
                            lineCap: .round,
                            lineJoin: .round,
                            dash: [0.5, 5.5]
                        )
                    )
                    .frame(
                        width: Self.posterSize + Self.posterFrameInset,
                        height: Self.posterSize + Self.posterFrameInset
                    )
                    .shadow(color: laughTrack.colors.accentStrong.opacity(0.6), radius: 3.5)
                    .shadow(color: laughTrack.colors.accentStrong.opacity(0.28), radius: 8)
            }
            .frame(
                width: Self.posterSize + Self.posterFrameInset,
                height: Self.posterSize + Self.posterFrameInset
            )

            Text(comedian.name)
                .font(laughTrack.typography.metadata.weight(.semibold))
                .foregroundStyle(laughTrack.colors.textPrimary)
                .multilineTextAlignment(.center)
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)

            if let role = ShowLineupPresentation.roleBadge(for: comedian) {
                Text(role)
                    .font(laughTrack.typography.metadata.weight(.bold))
                    .textCase(.uppercase)
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
            }
        }
        .frame(width: Self.tileWidth)
    }

    @ViewBuilder
    private var photo: some View {
        let laughTrack = theme.laughTrackTokens
        let trimmed = comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        let url = URL.normalizedExternalURL(trimmed)

        if let url {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                Rectangle()
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                fallbackPhoto
            }
        } else {
            fallbackPhoto
        }
    }

    private var fallbackPhoto: some View {
        let laughTrack = theme.laughTrackTokens

        return Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "music.mic")
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
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
                    eyebrow: "Can’t make it?",
                    title: "Shows you might like instead",
                    subtitle: nil
                )

                if relatedShows.isEmpty {
                    EmptyCard(message: "No related shows are available yet.")
                } else {
                    ForEach(relatedShows, id: \.id) { related in
                        Button {
                            openDetail(related)
                        } label: {
                            ShowRow(show: related, presentation: .compactTicket)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }
}

/// Admin-only badge surfacing the underlying `show.id` on the show-detail
/// screen so admin operators can grab the ID directly for triage. Tapping the
/// badge copies the ID to the clipboard. Visibility is gated upstream by
/// `authManager.currentUser?.isAdmin`; this view does not re-check the role.
private struct AdminShowIDBadge: View {
    let showID: Int

    @Environment(\.appTheme) private var theme
    @State private var copied = false

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button {
            #if canImport(UIKit)
            UIPasteboard.general.string = String(showID)
            #endif
            copied = true
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                copied = false
            }
        } label: {
            HStack(spacing: 6) {
                Image(systemName: copied ? "checkmark" : "doc.on.doc")
                    .font(.system(size: 11, weight: .semibold))
                Text(copied ? "Copied" : "Show ID: \(showID)")
                    .font(.system(.caption, design: .monospaced).weight(.semibold))
            }
            .foregroundStyle(laughTrack.colors.textSecondary)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(laughTrack.colors.surfaceMuted)
            .clipShape(Capsule())
            .overlay(
                Capsule()
                    .stroke(laughTrack.colors.textSecondary.opacity(0.25), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Show ID \(showID)")
        .accessibilityHint("Admin-only. Copies the show ID to the clipboard.")
    }
}
