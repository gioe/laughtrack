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
        let isSoldOut = show.soldOut == true
        let artworkComedian = isOpenMic ? nil : Self.artworkComedian(for: show)
        let lineup = isOpenMic ? [] : Self.topLineup(for: show, limit: 3, excluding: artworkComedian)
        let metadata = Self.metadata(for: show)

        return VStack(alignment: .leading, spacing: theme.spacing.sm) {
            HStack(alignment: .top, spacing: theme.spacing.md) {
                artworkColumn(isSoldOut: isSoldOut, caption: artworkComedian?.name)

                VStack(alignment: .leading, spacing: theme.spacing.xxs) {
                    Text(Self.listTitle(for: show))
                        .font(isOpenMic ? laughTrack.typography.metadata : laughTrack.typography.cardTitle)
                        .fontWeight(isOpenMic ? .semibold : nil)
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .lineLimit(isOpenMic ? 1 : 2)
                        .fixedSize(horizontal: false, vertical: true)

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

                    if !isOpenMic {
                        badgeRow(isSoldOut: isSoldOut)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .layoutPriority(1)
            }

            if !lineup.isEmpty {
                LineupAvatarStrip(
                    comedians: lineup.map(LineupAvatarItem.init(comedian:)),
                    isDimmed: isSoldOut,
                    openComedian: { coordinator.open(.comedian($0)) }
                )
            }
        }
        .frame(maxWidth: .infinity, minHeight: isOpenMic ? 56 : 86, alignment: .leading)
        .padding(.horizontal, laughTrack.browseDensity.compactCardPadding)
        .padding(.vertical, isOpenMic ? theme.spacing.sm : laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceMuted)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderStrong.opacity(0.55), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    @ViewBuilder
    private func artworkColumn(isSoldOut: Bool, caption: String?) -> some View {
        let laughTrack = theme.laughTrackTokens
        VStack(spacing: 4) {
            rowArtwork(isSoldOut: isSoldOut)
            if let caption, !caption.isEmpty {
                Text(caption)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                    .frame(width: LaughTrackEntityRowDesign.searchCard.artworkSize)
                    .opacity(isSoldOut ? 0.6 : 1)
            }
        }
    }

    @ViewBuilder
    private func rowArtwork(isSoldOut: Bool) -> some View {
        let laughTrack = theme.laughTrackTokens
        let rawImageURL = Self.artworkImageURL(for: show)

        Group {
            if let url = URL.normalizedExternalURL(rawImageURL) {
                CachedAsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    rowArtworkBackground
                        .overlay {
                            ProgressView()
                                .tint(laughTrack.colors.accent)
                        }
                } error: { _ in
                    rowArtworkFallback
                }
            } else {
                rowArtworkFallback
            }
        }
        .frame(
            width: LaughTrackEntityRowDesign.searchCard.artworkSize,
            height: LaughTrackEntityRowDesign.searchCard.artworkSize
        )
        .clipShape(Circle())
        .saturation(isSoldOut ? 0 : 1)
        .opacity(isSoldOut ? 0.6 : 1)
        .accessibilityHidden(true)
    }

    private var rowArtworkBackground: some View {
        Circle()
            .fill(theme.laughTrackTokens.colors.surfaceMuted)
    }

    private var rowArtworkFallback: some View {
        rowArtworkBackground
            .overlay {
                Image(systemName: "music.mic")
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(theme.laughTrackTokens.colors.accentStrong)
            }
    }

    @ViewBuilder
    private func badgeRow(isSoldOut: Bool) -> some View {
        let laughTrack = theme.laughTrackTokens
        let priceText = isSoldOut
            ? Self.previousPriceLabel(for: show)
            : Self.priceLabel(for: show)

        HStack(spacing: theme.spacing.xs) {
            if let priceText {
                Text(priceText)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .strikethrough(isSoldOut, color: laughTrack.colors.textSecondary)
                    .lineLimit(1)
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
