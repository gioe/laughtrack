import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge

struct ShowRow: View {
    let show: Components.Schemas.Show
    var nearbyRadiusMiles: Double?

    var body: some View {
        LaughTrackEntityRow(
            title: Self.listTitle(for: show),
            subtitle: show.clubName ?? "Unknown club",
            metadata: metadata,
            systemImage: "ticket.fill",
            imageURL: Self.artworkImageURL(for: show),
            showsDisclosureIndicator: true
        )
    }

    private var metadata: [String] {
        var values = Self.metadata(for: show)
        if isWithinNearbyRadius {
            values.append("Near you")
        }
        return values
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

    static func metadata(for show: Components.Schemas.Show) -> [String] {
        [
            ShowFormatting.listDate(show.date, timezoneID: show.timezone),
            Self.priceLabel(for: show),
            show.soldOut == true ? "Sold out" : nil,
        ].compactMap { $0 }
    }

    static func artworkImageURL(for show: Components.Schemas.Show) -> String? {
        let imageURL = featuredComedian(for: show)?.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        return imageURL?.isEmpty == false ? imageURL : nil
    }

    static func priceLabel(for show: Components.Schemas.Show) -> String? {
        let prices = (show.tickets ?? [])
            .filter { $0.soldOut != true }
            .compactMap(\.price)
            .sorted()

        guard let lowestPrice = prices.first else {
            return nil
        }

        guard let highestPrice = prices.last, highestPrice != lowestPrice else {
            return formatPrice(lowestPrice)
        }

        if lowestPrice == 0 {
            return "Free - \(formatPrice(highestPrice))"
        }

        return "\(formatPrice(lowestPrice)) - \(formatPrice(highestPrice))"
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

    private static func effectiveComedian(_ comedian: Components.Schemas.ComedianLineup) -> Components.Schemas.ComedianLineup {
        comedian.parentComedian ?? comedian
    }

    private static func formatPrice(_ price: Double) -> String {
        if price == 0 {
            return "Free"
        }

        if price.rounded() == price {
            return "$\(Int(price))"
        }

        return price.formatted(.currency(code: "USD"))
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

        if isLineupOnlyTitle(title, lineup: lineup) || isLikelyPerformerOnlyTitle(title) {
            return fallbackTitle(clubName: clubName)
        }

        return title
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
