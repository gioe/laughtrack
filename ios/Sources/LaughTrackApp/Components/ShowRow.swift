import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge

struct ShowRow: View {
    let show: Components.Schemas.Show

    var body: some View {
        LaughTrackResultRow(
            title: Self.title(for: show),
            subtitle: show.clubName ?? "Unknown club",
            metadata: [
                ShowFormatting.listDate(show.date, timezoneID: show.timezone),
                ShowFormatting.distance(show.distanceMiles),
                Self.priceLabel(for: show),
                show.soldOut == true ? "Sold out" : nil,
            ].compactMap { $0 },
            systemImage: "ticket.fill",
            imageURL: Self.artworkImageURL(for: show)
        )
    }

    static func title(for show: Components.Schemas.Show) -> String {
        let showName = show.name?.trimmingCharacters(in: .whitespacesAndNewlines)
        return showName?.isEmpty == false ? showName! : "Untitled show"
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
