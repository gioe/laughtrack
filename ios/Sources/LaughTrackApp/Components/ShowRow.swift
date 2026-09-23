import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge

enum ShowRowPresentation {
    case standard
    case compactTicket
    case compactTicketProminent
}

/// Agenda headings supply the date; independent tickets must carry their own.
enum ShowRowContext {
    case standalone
    case agenda
}

/// A reason supplied by the containing surface, never inferred from billing or artwork.
enum ShowRowPerformerContext: Equatable {
    case searchMatch(Int)
    case followed(Int)
    var comedianID: Int {
        switch self {
        case .searchMatch(let id), .followed(let id): id
        }
    }
    var reason: String {
        switch self {
        case .searchMatch: "Matches your comedian search"
        case .followed: "You follow"
        }
    }
}

struct ShowRow: View {
    static let artworkSlotSize: CGFloat = 60

    @Environment(\.appTheme) private var theme
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @Environment(\.redactionReasons) private var redactionReasons
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>

    let show: Components.Schemas.Show
    let presentation: ShowRowPresentation
    let preferredHeadlinerID: Int?
    let context: ShowRowContext
    let performerContext: ShowRowPerformerContext?

    init(
        show: Components.Schemas.Show,
        presentation: ShowRowPresentation = .standard,
        preferredHeadlinerID: Int? = nil,
        context: ShowRowContext = .standalone,
        performerContext: ShowRowPerformerContext? = nil
    ) {
        self.show = show
        self.presentation = presentation
        self.preferredHeadlinerID = preferredHeadlinerID
        self.context = context
        self.performerContext = performerContext
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        // Open mics share the same ticket treatment as other shows.
        return ticketContent
            .background(ticketPaper)
            .overlay(
                RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                    .stroke(ticketBorder, lineWidth: ticketBorderLineWidth)
            )
            .overlay(alignment: .leading) {
                if presentation == .compactTicketProminent {
                    ticketEdgeAccent
                        .frame(width: 4)
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
            .shadowStyle(laughTrack.shadows.card)
            .shadow(
                color: presentation == .compactTicketProminent
                    ? Color(red: 0.40, green: 0.18, blue: 0.06).opacity(0.12)
                    : .clear,
                radius: 8,
                x: 0,
                y: 4
            )
    }

    private var ticketPaper: Color {
        switch presentation {
        case .standard:
            theme.laughTrackTokens.colors.surfaceElevated
        case .compactTicket:
            Color(red: 0.93, green: 0.87, blue: 0.74)
        case .compactTicketProminent:
            Color(red: 0.96, green: 0.89, blue: 0.70)
        }
    }

    private var ticketInk: Color {
        switch presentation {
        case .standard:
            theme.laughTrackTokens.colors.textPrimary
        case .compactTicket, .compactTicketProminent:
            Color(red: 0.15, green: 0.10, blue: 0.05)
        }
    }

    private var ticketInkMuted: Color {
        switch presentation {
        case .standard:
            theme.laughTrackTokens.colors.textSecondary
        case .compactTicket:
            Color(red: 0.45, green: 0.35, blue: 0.22)
        case .compactTicketProminent:
            Color(red: 0.39, green: 0.27, blue: 0.12)
        }
    }

    private var ticketBorder: Color {
        switch presentation {
        case .standard:
            theme.laughTrackTokens.colors.borderStrong.opacity(0.9)
        case .compactTicket:
            Color(red: 0.58, green: 0.47, blue: 0.31).opacity(0.78)
        case .compactTicketProminent:
            Color(red: 0.59, green: 0.23, blue: 0.10).opacity(0.78)
        }
    }

    private var ticketBorderLineWidth: CGFloat {
        switch presentation {
        case .standard:
            1
        case .compactTicket:
            1.2
        case .compactTicketProminent:
            1.5
        }
    }

    private var ticketStubBackground: Color {
        switch presentation {
        case .standard:
            theme.laughTrackTokens.colors.surfaceMuted
        case .compactTicket:
            Color(red: 0.86, green: 0.78, blue: 0.63)
        case .compactTicketProminent:
            Color(red: 0.88, green: 0.76, blue: 0.49)
        }
    }

    private var ticketAccent: Color {
        switch presentation {
        case .standard:
            theme.laughTrackTokens.colors.accentStrong
        case .compactTicket:
            Color(red: 0.74, green: 0.30, blue: 0.13)
        case .compactTicketProminent:
            Color(red: 0.63, green: 0.24, blue: 0.08)
        }
    }

    private var ticketEdgeAccent: Color {
        Color(red: 0.67, green: 0.27, blue: 0.10).opacity(0.9)
    }

    // MARK: - Ticket-stub row

    @ViewBuilder
    private var ticketContent: some View {
        if context == .agenda {
            agendaTicket
        } else {
            ticketStubRow
        }
    }

    private var agendaTicket: some View {
        VStack(spacing: 0) {
            agendaTiming
                .padding(.horizontal, theme.laughTrackTokens.browseDensity.compactCardPadding)
                .padding(.vertical, theme.spacing.sm)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(ticketStubBackground)

            DashedHorizontalLine()
                .stroke(ticketInkMuted.opacity(0.45), style: StrokeStyle(lineWidth: 1, dash: [3, 3]))
                .frame(height: 1)
                .padding(.horizontal, theme.spacing.sm)

            ticketBody
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .fixedSize(horizontal: false, vertical: true)
    }

    private var agendaTiming: some View {
        let isSoldOut = show.soldOut == true
        let price = isSoldOut ? Self.previousPriceLabel(for: show) : Self.priceLabel(for: show)
        let layout = dynamicTypeSize.isAccessibilitySize
            ? AnyLayout(VStackLayout(alignment: .leading, spacing: theme.spacing.xs))
            : AnyLayout(HStackLayout(alignment: .firstTextBaseline, spacing: theme.spacing.sm))

        return layout {
            Text(Self.timeLabel(for: show))
                .font(theme.laughTrackTokens.typography.bodyEmphasis)
                .monospacedDigit()
                .foregroundStyle(ticketInk)
                .fixedSize(horizontal: false, vertical: true)
                .preservingSkeletonTextLayout()
                .frame(maxWidth: .infinity, alignment: .leading)

            if let price {
                Text(price)
                    .font(theme.laughTrackTokens.typography.metadata.weight(.semibold))
                    .monospacedDigit()
                    .foregroundStyle(ticketAccent)
                    .strikethrough(isSoldOut, color: ticketInkMuted)
                    .fixedSize(horizontal: false, vertical: true)
                    .preservingSkeletonTextLayout()
            }
        }
    }

    private var artworkTextLayout: AnyLayout {
        if dynamicTypeSize.isAccessibilitySize {
            AnyLayout(VStackLayout(alignment: .leading, spacing: theme.spacing.sm))
        } else {
            AnyLayout(HStackLayout(alignment: .center, spacing: theme.spacing.sm))
        }
    }

    private var ticketStubRow: some View {
        HStack(spacing: 0) {
            ticketBody
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)

            DashedVerticalLine()
                .stroke(
                    ticketInkMuted.opacity(presentation == .compactTicket ? 0.45 : 0.6),
                    style: StrokeStyle(lineWidth: 1, dash: [3, 3])
                )
                .frame(width: 1)
                .padding(.vertical, theme.spacing.sm)

            ticketStub
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .fixedSize(horizontal: false, vertical: true)
    }

    private var ticketBody: some View {
        let relevant = Self.contextualComedian(for: show, context: performerContext)
        let primary = relevant ?? Self.lineupPortraitComedian(for: show, preferredComedianID: preferredHeadlinerID)
        let remaining = Self.supportingLineup(for: show, excluding: primary)
        return VStack(alignment: .leading, spacing: theme.spacing.sm) {
            if let relevant, let performerContext {
                VStack(alignment: .leading, spacing: theme.spacing.xs) {
                    sectionCaption(performerContext.reason)
                    performerIdentity(relevant)
                }
                eventDetails
                if !remaining.isEmpty {
                    lineupBand {
                        sectionCaption("Also on the lineup")
                        rosterText(remaining)
                    }
                }
            } else {
                eventDetails
                lineupBand {
                    sectionCaption("Lineup")
                    if let primary {
                        artworkTextLayout {
                            portrait(for: primary)
                            VStack(alignment: .leading, spacing: theme.spacing.xs) {
                                performerName(primary.name)
                                if !remaining.isEmpty { rosterText(remaining) }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    } else {
                        Text("Lineup unavailable")
                            .font(theme.laughTrackTokens.typography.metadata)
                            .foregroundStyle(ticketInkMuted)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
            if show.soldOut == true || Self.isOpenMic(show) {
                ticketBodyBadges(isSoldOut: show.soldOut == true, isOpenMic: Self.isOpenMic(show))
            }
        }
        .padding(theme.laughTrackTokens.browseDensity.compactCardPadding)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
        .background(ticketBodyBackground)
    }

    private var eventDetails: some View {
        VStack(alignment: .leading, spacing: theme.spacing.xxs) {
            Text(Self.cardTitle(for: show))
                .font(theme.laughTrackTokens.typography.bodyEmphasis)
                .foregroundStyle(ticketInk)
                .fixedSize(horizontal: false, vertical: true)
                .preservingSkeletonTextLayout()
            if let venue = Self.venueLine(for: show) {
                Text(venue)
                    .font(theme.laughTrackTokens.typography.metadata)
                    .foregroundStyle(ticketInkMuted)
                    .fixedSize(horizontal: false, vertical: true)
                    .preservingSkeletonTextLayout()
            }
            if let room = Self.roomLabel(for: show) {
                Text(room)
                    .font(theme.laughTrackTokens.typography.metadata)
                    .foregroundStyle(ticketInkMuted)
                    .fixedSize(horizontal: false, vertical: true)
                    .preservingSkeletonTextLayout()
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func sectionCaption(_ title: String) -> some View {
        Text(title)
            .font(theme.laughTrackTokens.typography.metadata.weight(.semibold))
            .foregroundStyle(ticketInkMuted)
            .fixedSize(horizontal: false, vertical: true)
            .preservingSkeletonTextLayout()
    }

    private func lineupBand<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: theme.spacing.xs, content: content)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(theme.spacing.sm)
            .background(ticketInk.opacity(0.035), in: RoundedRectangle(cornerRadius: 10))
    }

    private func performerName(_ name: String, prominent: Bool = false) -> some View {
        Text(name)
            .font(prominent ? theme.laughTrackTokens.typography.sectionTitle : theme.laughTrackTokens.typography.bodyEmphasis)
            .foregroundStyle(ticketInk)
            .fixedSize(horizontal: false, vertical: true)
            .preservingSkeletonTextLayout()
    }

    private func performerIdentity(_ comedian: Components.Schemas.ComedianLineup) -> some View {
        artworkTextLayout {
            portrait(for: comedian)
            performerName(comedian.name, prominent: true)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func rosterText(_ comedians: [Components.Schemas.ComedianLineup]) -> some View {
        Text(Self.lineupPreview(for: comedians))
            .font(theme.laughTrackTokens.typography.metadata)
            .foregroundStyle(ticketInkMuted)
            .fixedSize(horizontal: false, vertical: true)
            .preservingSkeletonTextLayout()
    }

    private var ticketBodyBackground: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            ticketPaper
            switch presentation {
            case .standard:
                laughTrack.colors.accent.opacity(0.035)
            case .compactTicket:
                LinearGradient(
                    colors: [
                        Color.white.opacity(0.24),
                        laughTrack.colors.accentStrong.opacity(0.10),
                        Color.black.opacity(0.03)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            case .compactTicketProminent:
                LinearGradient(
                    colors: [
                        Color.white.opacity(0.30),
                        laughTrack.colors.accentStrong.opacity(0.13),
                        Color(red: 0.91, green: 0.62, blue: 0.22).opacity(0.12),
                        Color.black.opacity(0.025)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            }
        }
    }

    private func portrait(for comedian: Components.Schemas.ComedianLineup) -> some View {
        Group {
            if redactionReasons.contains(.placeholder) {
                Circle().fill(ticketInk.opacity(0.12))
            } else if let rawURL = Self.absoluteArtworkImageURL(comedian.imageUrl), let url = URL(string: rawURL) {
                CachedAsyncImage(url: url) { image in
                    image.resizable().scaledToFill()
                } placeholder: {
                    portraitFallback
                } error: { _ in
                    portraitFallback
                }
            } else {
                portraitFallback
            }
        }
        .frame(width: Self.artworkSlotSize, height: Self.artworkSlotSize)
        .clipShape(Circle())
        .overlay(Circle().stroke(ticketInkMuted.opacity(0.3), lineWidth: 1))
        .accessibilityHidden(true)
    }

    private var portraitFallback: some View {
        Circle()
            .fill(ticketInk.opacity(0.08))
            .overlay {
                Image(systemName: ArtworkFallbackKind.person.systemImage)
                    .font(.system(size: 22, weight: .medium))
                    .foregroundStyle(ticketInkMuted)
            }
    }

    @ViewBuilder
    private func ticketBodyBadges(isSoldOut: Bool, isOpenMic: Bool) -> some View {
        let laughTrack = theme.laughTrackTokens
        let layout = context == .agenda && dynamicTypeSize.isAccessibilitySize
            ? AnyLayout(VStackLayout(alignment: .leading, spacing: theme.spacing.xs))
            : AnyLayout(HStackLayout(spacing: theme.spacing.xs))

        layout {
            if isOpenMic {
                HStack(spacing: 4) {
                    Image(systemName: "music.mic")
                        .font(.system(size: 10, weight: .bold))
                    Text("Open mic")
                        .font(laughTrack.typography.metadata.weight(.semibold))
                }
                .foregroundStyle(laughTrack.colors.accentStrong)
                .padding(.horizontal, theme.spacing.xs)
                .padding(.vertical, 2)
                .background(
                    Capsule(style: .continuous)
                        .fill(laughTrack.colors.accentMuted.opacity(0.22))
                )
                .overlay(
                    Capsule(style: .continuous)
                        .stroke(laughTrack.colors.accentMuted.opacity(0.45), lineWidth: 1)
                )
            }

            if isSoldOut {
                Text("Sold out")
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.danger)
                    .padding(.horizontal, theme.spacing.xs)
                    .padding(.vertical, 2)
                    .background(
                        Capsule(style: .continuous)
                            .fill(laughTrack.colors.danger.opacity(0.12))
                    )
            }

        }
    }

    private var ticketStub: some View {
        let isSoldOut = show.soldOut == true
        let stack = ShowFormatting.dateStack(show.date, timezoneID: show.timezone)
        let monthText = Self.monthAbbreviation(show.date, timezoneID: show.timezone)
        let priceText = isSoldOut
            ? Self.previousPriceLabel(for: show)
            : Self.priceLabel(for: show)

        return VStack(spacing: 3) {
            Text(stack.weekday)
                .font(.system(size: 11, weight: .semibold, design: .rounded))
                .tracking(1.4)
                .foregroundStyle(ticketAccent)

            Text(stack.day)
                .font(.system(size: 26, weight: .heavy, design: .rounded))
                .foregroundStyle(ticketInk)
                .monospacedDigit()

            Text(monthText)
                .font(.system(size: 11, weight: .semibold, design: .rounded))
                .tracking(1.2)
                .foregroundStyle(ticketInkMuted)

            Text(stack.time)
                .font(.system(size: 11, weight: .medium, design: .rounded))
                .foregroundStyle(ticketInkMuted)
                .monospacedDigit()
                .padding(.top, 2)

            if let priceText {
                Text(priceText)
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .foregroundStyle(ticketAccent)
                    .strikethrough(isSoldOut, color: ticketInkMuted)
                    .monospacedDigit()
            }
        }
        .frame(width: 88)
        .frame(maxHeight: .infinity)
        .padding(.vertical, theme.spacing.sm)
        .background(ticketStubBackground)
    }

    // Timezone-keyed month-abbreviation formatter cache. Each entry is configured
    // once and never mutated again, replacing the former per-call `.timeZone`
    // mutation of a shared `static let` (a DateFormatter data race). @MainActor
    // isolation matches the call site (the SwiftUI ticket-stub view body) (TASK-3663).
    @MainActor private static var monthStackFormatters: [String: DateFormatter] = [:]

    @MainActor
    private static func monthAbbreviation(_ date: Date, timezoneID: String?) -> String {
        let resolved = timezoneID.flatMap(TimeZone.init(identifier:)) ?? TimeZone.current
        if let existing = monthStackFormatters[resolved.identifier] {
            return existing.string(from: date).uppercased()
        }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "MMM"
        formatter.timeZone = resolved
        monthStackFormatters[resolved.identifier] = formatter
        return formatter.string(from: date).uppercased()
    }

    /// Keep supplied event information intact; a roster is not evidence of billing.
    static func cardTitle(for show: Components.Schemas.Show) -> String {
        let title = show.name?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return title.isEmpty ? "Comedy show" : title
    }

    static func contextualComedian(
        for show: Components.Schemas.Show,
        context: ShowRowPerformerContext?
    ) -> Components.Schemas.ComedianLineup? {
        guard let context else { return nil }
        return topLineup(for: show, limit: .max).first { $0.id == context.comedianID }
    }

    static func lineupPortraitComedian(
        for show: Components.Schemas.Show,
        preferredComedianID: Int? = nil
    ) -> Components.Schemas.ComedianLineup? {
        artworkComedian(for: show, preferredComedianID: preferredComedianID)
            ?? topLineup(for: show, limit: 1).first
    }

    static func lineupPreview(for comedians: [Components.Schemas.ComedianLineup], visibleLimit: Int = 3) -> String {
        var seen = Set<Int>()
        let unique = comedians.map(effectiveComedian).filter { seen.insert($0.id).inserted }
        let visible = unique.prefix(max(1, visibleLimit))
        let names = visible.map(\.name).joined(separator: ", ")
        let overflow = unique.count - visible.count
        return overflow > 0 ? "\(names) · +\(overflow) more" : names
    }

    static func title(for show: Components.Schemas.Show) -> String {
        ShowTitlePresentation.title(for: show)
    }

    static func listTitle(for show: Components.Schemas.Show) -> String {
        let title = ShowTitlePresentation.title(for: show)
        let clubName = show.clubName?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !clubName.isEmpty, title == "Comedy Show at \(clubName)" else {
            return title
        }

        return "Comedy show"
    }

    static func primaryListTitle(
        for show: Components.Schemas.Show,
        headliner: Components.Schemas.ComedianLineup
    ) -> String {
        let eventTitle = listTitle(for: show)
        return eventTitle == "Comedy show" ? headliner.name : eventTitle
    }

    static func headlinerContext(
        for show: Components.Schemas.Show,
        headliner: Components.Schemas.ComedianLineup,
        context: ShowRowContext = .standalone
    ) -> String? {
        let primaryTitle = primaryListTitle(for: show, headliner: headliner)
        guard primaryTitle.localizedCaseInsensitiveCompare(headliner.name) != .orderedSame else {
            return nil
        }
        // A full performer name followed by a title separator already supplies
        // that identity. Keep aliases, partial names, and other event titles.
        if context == .agenda {
            let name = headliner.name.trimmingCharacters(in: .whitespacesAndNewlines)
            if !name.isEmpty {
                let generatedHeadline = primaryTitle.localizedCaseInsensitiveCompare("\(name) Headlines") == .orderedSame
                let namedEvent = [":", " & ", " - ", " – ", " — "].contains { separator in
                    primaryTitle.range(of: name + separator, options: [.anchored, .caseInsensitive]) != nil
                }
                if generatedHeadline || namedEvent { return nil }
            }
        }
        return headliner.name
    }

    @MainActor
    static func timeLabel(for show: Components.Schemas.Show) -> String {
        ShowFormatting.dateStack(show.date, timezoneID: show.timezone).time
    }

    static func venueLine(for show: Components.Schemas.Show) -> String? {
        let clubName = show.clubName?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !clubName.isEmpty else { return nil }

        let city = show.clubCity?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let state = show.clubState?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""

        if !city.isEmpty, !state.isEmpty {
            return "\(clubName) • \(city), \(state)"
        }
        if !city.isEmpty {
            return "\(clubName) • \(city)"
        }
        if !state.isEmpty {
            return "\(clubName) • \(state)"
        }
        return clubName
    }

    static func artworkImageURL(
        for show: Components.Schemas.Show,
        preferredComedianID: Int? = nil
    ) -> String? {
        if let comedian = artworkComedian(
            for: show,
            preferredComedianID: preferredComedianID
        ) {
            return absoluteArtworkImageURL(comedian.imageUrl)
        }
        return absoluteArtworkImageURL(show.imageUrl)
    }

    static func artworkComedian(
        for show: Components.Schemas.Show,
        preferredComedianID: Int? = nil
    ) -> Components.Schemas.ComedianLineup? {
        guard let lineup = show.lineup else { return nil }
        if let preferredComedianID,
           let preferred = lineup
            .map(effectiveComedian)
            .first(where: { $0.id == preferredComedianID }) {
            return preferred
        }
        return rankedLineup(lineup, requiringAbsoluteArtwork: true).first
    }

    static func absoluteArtworkImageURL(_ rawValue: String?) -> String? {
        let trimmed = rawValue?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard
            let url = URL(string: trimmed),
            let scheme = url.scheme?.lowercased(),
            scheme == "http" || scheme == "https",
            url.host?.isEmpty == false
        else {
            return nil
        }
        return trimmed
    }

    static func metadata(for show: Components.Schemas.Show) -> [String] {
        [
            ShowFormatting.listDate(show.date, timezoneID: show.timezone),
            roomLabel(for: show),
        ].compactMap { $0?.nonEmpty }
    }

    static func priceLabel(for show: Components.Schemas.Show) -> String? {
        ShowPricePresentation.rowPriceLabel(for: show)
    }

    static func previousPriceLabel(for show: Components.Schemas.Show) -> String? {
        ShowPricePresentation.rowPreviousPriceLabel(for: show)
    }

    static func roomLabel(for show: Components.Schemas.Show) -> String? {
        let room = show.room?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !room.isEmpty else { return nil }
        // Some scrapers copy the club name into room (e.g. ticketmaster,
        // show 1779237 "Punch Line Philly"), which would repeat the club
        // name rendered alongside this label. Mirrors the web guard from
        // TASK-2789.
        let clubName = show.clubName?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if room.caseInsensitiveCompare(clubName) == .orderedSame { return nil }
        return room
    }

    static func isOpenMic(_ show: Components.Schemas.Show) -> Bool {
        if ShowFormatting.isOpenMic(tags: show.tags) { return true }
        return ShowFormatting.isOpenMic(show.name)
    }

    static func topLineup(
        for show: Components.Schemas.Show,
        limit: Int = 3,
        excluding excluded: Components.Schemas.ComedianLineup? = nil
    ) -> [Components.Schemas.ComedianLineup] {
        guard let lineup = show.lineup, !lineup.isEmpty else { return [] }
        return Array(rankedLineup(lineup, excluding: excluded).prefix(limit))
    }

    static func supportingLineup(
        for show: Components.Schemas.Show,
        excluding headliner: Components.Schemas.ComedianLineup?
    ) -> [Components.Schemas.ComedianLineup] {
        topLineup(for: show, limit: .max, excluding: headliner)
    }

    static func supportingLabel(
        for supporting: [Components.Schemas.ComedianLineup],
        visibleLimit: Int = 3
    ) -> String {
        let visible = Array(supporting.prefix(visibleLimit))
        let names = visible.map(\.name).joined(separator: ", ")
        let overflow = max(0, supporting.count - visible.count)
        return overflow > 0
            ? "with \(names) +\(overflow) more"
            : "with \(names)"
    }

    static func effectiveComedian(_ comedian: Components.Schemas.ComedianLineup) -> Components.Schemas.ComedianLineup {
        comedian.parentComedian ?? comedian
    }

    private static func rankedLineup(
        _ lineup: [Components.Schemas.ComedianLineup],
        requiringAbsoluteArtwork: Bool = false,
        excluding excluded: Components.Schemas.ComedianLineup? = nil
    ) -> [Components.Schemas.ComedianLineup] {
        var seen = Set<Int>()
        return lineup.enumerated()
            .map { (offset: $0.offset, comedian: effectiveComedian($0.element)) }
            .filter { seen.insert($0.comedian.id).inserted }
            .filter { candidate in
                if let excluded, candidate.comedian.id == excluded.id {
                    return false
                }
                return !requiringAbsoluteArtwork
                    || absoluteArtworkImageURL(candidate.comedian.imageUrl) != nil
            }
            .sorted { lhs, rhs in
                let lhsPopularity = lhs.comedian.socialData?.popularity ?? -1
                let rhsPopularity = rhs.comedian.socialData?.popularity ?? -1
                if lhsPopularity != rhsPopularity {
                    return lhsPopularity > rhsPopularity
                }

                let lhsCount = lhs.comedian.showCount ?? 0
                let rhsCount = rhs.comedian.showCount ?? 0
                if lhsCount != rhsCount {
                    return lhsCount > rhsCount
                }

                return lhs.offset < rhs.offset
            }
            .map(\.comedian)
    }

}

/// Perforation between the agenda's timing strip and show details.
private struct DashedHorizontalLine: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.minX, y: rect.midY))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.midY))
        return path
    }
}

/// Perforation between standalone show details and the date/price stub.
private struct DashedVerticalLine: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.midX, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.midX, y: rect.maxY))
        return path
    }
}

enum ShowTitlePresentation {
    static func title(for show: Components.Schemas.Show) -> String {
        displayTitle(
            rawTitle: show.name,
            clubName: show.clubName,
            lineup: show.lineup
        )
    }

    static func title(for show: Components.Schemas.ShowDetail) -> String {
        displayTitle(
            rawTitle: show.name,
            clubName: show.club.name,
            lineup: show.lineup
        )
    }

    private static func displayTitle(
        rawTitle: String?,
        clubName: String?,
        lineup: [Components.Schemas.ComedianLineup]?
    ) -> String {
        let title = rawTitle?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if title.isEmpty {
            return fallbackTitle(clubName: clubName)
        }

        if isLineupOnlyTitle(title, lineup: lineup) {
            return performerHeadlineTitle(performerName: title)
        }

        if isLikelyPerformerOnlyTitle(title) {
            return fallbackTitle(clubName: clubName)
        }

        return title
    }

    private static func performerHeadlineTitle(performerName: String) -> String {
        "\(performerName) Headlines"
    }

    private static func isLineupOnlyTitle(
        _ title: String,
        lineup: [Components.Schemas.ComedianLineup]?
    ) -> Bool {
        guard let lineup, lineup.count == 1 else {
            return false
        }

        let comedian = lineup[0]
        let names = [
            comedian.name,
            comedian.parentComedian?.name
        ]

        return names.contains { name in
            guard let name else { return false }
            return name.trimmingCharacters(in: .whitespacesAndNewlines)
                .localizedCaseInsensitiveCompare(title) == .orderedSame
        }
    }

    private static func fallbackTitle(clubName: String?) -> String {
        let clubName = clubName?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return clubName.isEmpty ? "Comedy show" : "Comedy Show at \(clubName)"
    }

    private static func isLikelyPerformerOnlyTitle(_ title: String) -> Bool {
        let lowercased = title.lowercased()
        let showWords = [
            "comedy",
            "show",
            "showcase",
            "friends",
            "night",
            "live",
            "open",
            "mic",
            "late",
            "early",
            "set",
            "presents",
            "special",
            "festival"
        ]

        if showWords.contains(where: { lowercased.contains($0) }) {
            return false
        }

        let words = title
            .split(separator: " ")
            .map(String.init)
            .filter { !$0.isEmpty }

        guard (2...3).contains(words.count) else {
            return false
        }

        return words.allSatisfy { word in
            word.range(of: #"^[A-Z][A-Za-z.'-]*$"#, options: .regularExpression) != nil
        }
    }
}
