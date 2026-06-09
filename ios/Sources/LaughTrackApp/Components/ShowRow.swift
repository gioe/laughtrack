import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge

struct ShowRow: View {
    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>

    let show: Components.Schemas.Show
    var nearbyRadiusMiles: Double?

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let isOpenMic = Self.isOpenMic(show)

        return Group {
            if isOpenMic {
                openMicRow
            } else {
                ticketStubRow
            }
        }
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderStrong.opacity(0.9), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    // MARK: - Open mic row (compact)

    private var openMicRow: some View {
        let laughTrack = theme.laughTrackTokens
        let metadata = Self.metadata(for: show)

        return VStack(alignment: .leading, spacing: theme.spacing.xxs) {
            Text(Self.listTitle(for: show))
                .font(laughTrack.typography.metadata)
                .fontWeight(.semibold)
                .foregroundStyle(laughTrack.colors.textPrimary)
                .lineLimit(1)

            if let clubName = show.clubName, !clubName.isEmpty {
                Text(clubName)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(1)
            }

            if !metadata.isEmpty {
                Text(metadata.joined(separator: " • "))
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, minHeight: 56, alignment: .leading)
        .padding(.horizontal, laughTrack.browseDensity.compactCardPadding)
        .padding(.vertical, theme.spacing.sm)
    }

    // MARK: - Ticket-stub row

    private var ticketStubRow: some View {
        HStack(spacing: 0) {
            ticketBody
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)

            DashedVerticalLine()
                .stroke(
                    theme.laughTrackTokens.colors.borderStrong.opacity(0.6),
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

            if isSoldOut || isWithinNearbyRadius {
                ticketBodyBadges(isSoldOut: isSoldOut)
            }
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(ticketBodyBackground)
    }

    private var titleOnlyBlock: some View {
        let laughTrack = theme.laughTrackTokens
        let clubName = show.clubName?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let roomName = Self.roomLabel(for: show)

        return VStack(alignment: .leading, spacing: theme.spacing.xxs) {
            Text(Self.listTitle(for: show))
                .font(laughTrack.typography.bodyEmphasis)
                .foregroundStyle(laughTrack.colors.textPrimary)
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)

            if !clubName.isEmpty {
                Text(clubName)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(1)
            }

            if let roomName {
                Text(roomName)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(1)
            }
        }
    }

    private var ticketBodyBackground: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            laughTrack.colors.surfaceElevated
            laughTrack.colors.accent.opacity(0.035)
        }
    }

    @ViewBuilder
    private func headlinerBlock(
        headliner: Components.Schemas.ComedianLineup,
        supporting: [Components.Schemas.ComedianLineup],
        isSoldOut: Bool
    ) -> some View {
        let laughTrack = theme.laughTrackTokens
        let clubName = show.clubName?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""

        VStack(alignment: .leading, spacing: theme.spacing.xs) {
            HStack(alignment: .center, spacing: theme.spacing.sm) {
                headlinerAvatar(for: headliner)
                    .frame(width: 60, height: 60)
                    .clipShape(Circle())
                    .overlay(
                        Circle().stroke(
                            laughTrack.colors.accent.opacity(0.35),
                            lineWidth: 1.5
                        )
                    )

                VStack(alignment: .leading, spacing: 2) {
                    Text(headliner.name)
                        .font(laughTrack.typography.bodyEmphasis)
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)

                    if !clubName.isEmpty {
                        Text(clubName)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
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

    @ViewBuilder
    private func headlinerAvatar(for comedian: Components.Schemas.ComedianLineup) -> some View {
        let laughTrack = theme.laughTrackTokens
        let trimmed = comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        let normalized = trimmed.isEmpty ? nil : trimmed

        if let url = URL.normalizedExternalURL(normalized) {
            CachedAsyncImage(url: url) { image in
                image.resizable().scaledToFill()
            } placeholder: {
                Circle().fill(laughTrack.colors.surfaceMuted)
            } error: { _ in
                headlinerAvatarFallback
            }
        } else {
            headlinerAvatarFallback
        }
    }

    private var headlinerAvatarFallback: some View {
        let laughTrack = theme.laughTrackTokens
        return Circle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "person.fill")
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
                .foregroundStyle(laughTrack.colors.textSecondary)
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
                Image(systemName: "person.fill")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

    @ViewBuilder
    private func ticketBodyBadges(isSoldOut: Bool) -> some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.xs) {
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

            if isWithinNearbyRadius {
                Text("Near you")
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .padding(.horizontal, theme.spacing.xs)
                    .padding(.vertical, 2)
                    .background(
                        Capsule(style: .continuous)
                            .fill(laughTrack.colors.highlight.opacity(0.18))
                    )
            }
        }
    }

    private var ticketStub: some View {
        let laughTrack = theme.laughTrackTokens
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
                .foregroundStyle(laughTrack.colors.accentStrong)

            Text(stack.day)
                .font(.system(size: 26, weight: .heavy, design: .rounded))
                .foregroundStyle(laughTrack.colors.textPrimary)
                .monospacedDigit()

            Text(monthText)
                .font(.system(size: 11, weight: .semibold, design: .rounded))
                .tracking(1.2)
                .foregroundStyle(laughTrack.colors.textSecondary)

            Text(stack.time)
                .font(.system(size: 11, weight: .medium, design: .rounded))
                .foregroundStyle(laughTrack.colors.textSecondary)
                .monospacedDigit()
                .padding(.top, 2)

            if let priceText {
                Text(priceText)
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .strikethrough(isSoldOut, color: laughTrack.colors.textSecondary)
                    .monospacedDigit()
            }
        }
        .frame(width: 88)
        .frame(maxHeight: .infinity)
        .padding(.vertical, theme.spacing.sm)
        .background(laughTrack.colors.surfaceMuted)
    }

    private static let monthStackFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "MMM"
        return formatter
    }()

    private static func monthAbbreviation(_ date: Date, timezoneID: String?) -> String {
        let resolved = timezoneID.flatMap(TimeZone.init(identifier:)) ?? TimeZone.current
        monthStackFormatter.timeZone = resolved
        return monthStackFormatter.string(from: date).uppercased()
    }

    private var isWithinNearbyRadius: Bool {
        guard let distance = show.distanceMiles, let nearbyRadiusMiles else { return false }
        return distance <= nearbyRadiusMiles
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

    static func artworkImageURL(for show: Components.Schemas.Show) -> String? {
        artworkComedian(for: show)?.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
    }

    static func artworkComedian(for show: Components.Schemas.Show) -> Components.Schemas.ComedianLineup? {
        guard let featured = featuredComedian(for: show) else { return nil }
        let trimmed = featured.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : featured
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
        return room.isEmpty ? nil : room
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

    private static func featuredComedian(for show: Components.Schemas.Show) -> Components.Schemas.ComedianLineup? {
        guard let lineup = show.lineup, !lineup.isEmpty else {
            return nil
        }

        return lineup
            .map(effectiveComedian)
            .max { lhs, rhs in
                (lhs.showCount ?? 0) < (rhs.showCount ?? 0)
            }
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
