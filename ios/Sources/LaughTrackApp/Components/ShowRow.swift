import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge

enum ShowRowPresentation {
    case standard
    case compactTicket
    case compactTicketProminent
}

struct ShowRow: View {
    static let artworkSlotSize: CGFloat = 60

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>

    let show: Components.Schemas.Show
    let presentation: ShowRowPresentation

    init(
        show: Components.Schemas.Show,
        presentation: ShowRowPresentation = .standard
    ) {
        self.show = show
        self.presentation = presentation
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        // Open mics used to render a separate compact variant, but the
        // visual mismatch with the surrounding ticket-stub rows was the
        // bigger problem than the extra height — the unified ticket-stub
        // layout naturally falls through to titleOnlyBlock for shows
        // without a headliner, which covers every open mic.
        return ticketStubRow
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
        let laughTrack = theme.laughTrackTokens
        let isSoldOut = show.soldOut == true
        let isOpenMic = Self.isOpenMic(show)
        let headliner = Self.artworkComedian(for: show)
        let supporting = Self.topLineup(for: show, limit: 3, excluding: headliner)

        return VStack(alignment: .leading, spacing: theme.spacing.sm) {
            if let headliner {
                headlinerBlock(
                    headliner: headliner,
                    supporting: supporting,
                    isSoldOut: isSoldOut
                )
            } else {
                titleOnlyBlock
            }

            if isSoldOut || isOpenMic {
                ticketBodyBadges(isSoldOut: isSoldOut, isOpenMic: isOpenMic)
            }
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        // Vertically center the body so short title-only rows (e.g. a venue-
        // named show with no headliner) don't look top-stacked next to the
        // taller date stub on the trailing edge.
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
        .background(ticketBodyBackground)
    }

    private var titleOnlyBlock: some View {
        let laughTrack = theme.laughTrackTokens
        let venueLine = Self.venueLine(for: show)
        let roomName = Self.roomLabel(for: show)

        return HStack(alignment: .center, spacing: theme.spacing.sm) {
            artworkSlot

            VStack(alignment: .leading, spacing: theme.spacing.xxs) {
                Text(Self.listTitle(for: show))
                    .font(laughTrack.typography.bodyEmphasis)
                    .foregroundStyle(ticketInk)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)

                if let venueLine {
                    Text(venueLine)
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(ticketInkMuted)
                        .lineLimit(1)
                }

                if let roomName {
                    Text(roomName)
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(ticketInkMuted)
                        .lineLimit(1)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
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

    @ViewBuilder
    private func headlinerBlock(
        headliner: Components.Schemas.ComedianLineup,
        supporting: [Components.Schemas.ComedianLineup],
        isSoldOut: Bool
    ) -> some View {
        let laughTrack = theme.laughTrackTokens
        let venueLine = Self.venueLine(for: show)

        VStack(alignment: .leading, spacing: theme.spacing.xs) {
            HStack(alignment: .center, spacing: theme.spacing.sm) {
                artworkSlot

                VStack(alignment: .leading, spacing: 2) {
                    Text(Self.primaryListTitle(for: show, headliner: headliner))
                        .font(laughTrack.typography.bodyEmphasis)
                        .foregroundStyle(ticketInk)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)

                    if let headlinerContext = Self.headlinerContext(for: show, headliner: headliner) {
                        Text(headlinerContext)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(ticketInkMuted)
                            .lineLimit(1)
                    }

                    if let venueLine {
                        Text(venueLine)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(ticketInkMuted)
                            .lineLimit(1)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            if !supporting.isEmpty {
                supportingRow(supporting: supporting)
            }
        }
        .saturation(isSoldOut ? 0 : 1)
        .opacity(isSoldOut ? 0.6 : 1)
    }

    private var artworkSlot: some View {
        let laughTrack = theme.laughTrackTokens

        return artworkImage
            .frame(width: Self.artworkSlotSize, height: Self.artworkSlotSize)
            .clipShape(Circle())
            .overlay(
                Circle().stroke(
                    laughTrack.colors.accent.opacity(0.35),
                    lineWidth: 1.5
                )
            )
    }

    @ViewBuilder
    private var artworkImage: some View {
        let laughTrack = theme.laughTrackTokens

        if let rawURL = Self.artworkImageURL(for: show), let url = URL(string: rawURL) {
            CachedAsyncImage(url: url) { image in
                image.resizable().scaledToFill()
            } placeholder: {
                Circle().fill(laughTrack.colors.surfaceMuted)
            } error: { _ in
                artworkFallback
            }
        } else {
            artworkFallback
        }
    }

    private var artworkFallback: some View {
        let laughTrack = theme.laughTrackTokens
        return Circle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: ArtworkFallbackKind.show.systemImage)
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

    @ViewBuilder
    private func supportingRow(supporting: [Components.Schemas.ComedianLineup]) -> some View {
        let laughTrack = theme.laughTrackTokens
        let stackedAvatars = Array(supporting.prefix(3))
        let names = stackedAvatars.map(\.name).joined(separator: ", ")
        let overflow = max(0, supporting.count - stackedAvatars.count)
        let label = overflow > 0
            ? "with \(names) +\(overflow) more"
            : "with \(names)"

        HStack(spacing: theme.spacing.xs) {
            if !stackedAvatars.isEmpty {
                ZStack(alignment: .leading) {
                    ForEach(Array(stackedAvatars.enumerated()), id: \.element.id) { index, comedian in
                        supportingAvatar(for: comedian)
                            .overlay(
                                Circle().stroke(laughTrack.colors.surfaceElevated, lineWidth: 2)
                            )
                            .offset(x: CGFloat(index) * 16)
                            .zIndex(Double(stackedAvatars.count - index))
                    }
                }
                .frame(
                    width: 24 + CGFloat(max(0, stackedAvatars.count - 1)) * 16,
                    height: 24,
                    alignment: .leading
                )
            }

            Text(label)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(ticketInkMuted)
                .lineLimit(3)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    @ViewBuilder
    private func supportingAvatar(for comedian: Components.Schemas.ComedianLineup) -> some View {
        let laughTrack = theme.laughTrackTokens
        let trimmed = comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        let normalized = trimmed.isEmpty ? nil : trimmed

        Group {
            if let url = URL.normalizedExternalURL(normalized) {
                CachedAsyncImage(url: url) { image in
                    image.resizable().scaledToFill()
                } placeholder: {
                    Circle().fill(laughTrack.colors.surfaceMuted)
                } error: { _ in
                    supportingAvatarFallback
                }
            } else {
                supportingAvatarFallback
            }
        }
        .frame(width: 24, height: 24)
        .clipShape(Circle())
    }

    private var supportingAvatarFallback: some View {
        let laughTrack = theme.laughTrackTokens
        return Circle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: ArtworkFallbackKind.person.systemImage)
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

    @ViewBuilder
    private func ticketBodyBadges(isSoldOut: Bool, isOpenMic: Bool) -> some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.xs) {
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
        headliner: Components.Schemas.ComedianLineup
    ) -> String? {
        let primaryTitle = primaryListTitle(for: show, headliner: headliner)
        guard primaryTitle.localizedCaseInsensitiveCompare(headliner.name) != .orderedSame else {
            return nil
        }
        return headliner.name
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

    static func artworkImageURL(for show: Components.Schemas.Show) -> String? {
        if let comedian = artworkComedian(for: show) {
            return absoluteArtworkImageURL(comedian.imageUrl)
        }
        return absoluteArtworkImageURL(show.imageUrl)
    }

    static func artworkComedian(for show: Components.Schemas.Show) -> Components.Schemas.ComedianLineup? {
        show.lineup?
            .map(effectiveComedian)
            .filter { absoluteArtworkImageURL($0.imageUrl) != nil }
            .max { lhs, rhs in
                (lhs.showCount ?? 0) < (rhs.showCount ?? 0)
            }
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

        let resolved = lineup.map(Self.effectiveComedian)
        let filtered: [Components.Schemas.ComedianLineup]
        if let excluded {
            filtered = resolved.filter { $0.id != excluded.id }
        } else {
            filtered = resolved
        }
        let counts = filtered.compactMap(\.showCount)
        let ordered: [Components.Schemas.ComedianLineup]
        if counts.isEmpty {
            ordered = filtered
        } else {
            ordered = filtered.sorted { ($0.showCount ?? 0) > ($1.showCount ?? 0) }
        }

        return Array(ordered.prefix(limit))
    }

    static func effectiveComedian(_ comedian: Components.Schemas.ComedianLineup) -> Components.Schemas.ComedianLineup {
        comedian.parentComedian ?? comedian
    }

}

/// Simple vertical line used as the perforation between the show card body and
/// the date/price stub. Stroke styles (color + dash pattern) are applied at the
/// callsite so the same shape can serve other ticket-style splits later.
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
