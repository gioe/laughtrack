import Foundation
import LaughTrackAPIClient

enum ShowPricePresentation {
    static func rowPriceLabel(for show: Components.Schemas.Show) -> String? {
        priceRangeLabel(from: show.tickets, includeSoldOut: false)
    }

    static func rowPreviousPriceLabel(for show: Components.Schemas.Show) -> String? {
        priceRangeLabel(from: show.tickets, includeSoldOut: true)
    }

    static func detailTicketSummary(for show: Components.Schemas.ShowDetail) -> String {
        if show.cta.isSoldOut || show.soldOut == true {
            return "Sold out"
        }

        let prices = (show.tickets ?? []).compactMap(\.price)
        guard let lowest = prices.min() else {
            return "Price unavailable"
        }

        if lowest <= 0 {
            return "Free"
        }

        return currencyFormatter.string(from: NSNumber(value: lowest)) ?? "$\(lowest)"
    }

    static func detailTicketPriceUnavailable(_ summary: String) -> Bool {
        summary == "Price unavailable"
    }

    static let priceUnavailableExplanation = "Price of these tickets was not made available to us by the venue."

    // Rows stay compact for scannable lists and expose the lowest available
    // tier as "From $X" rather than a "$X - $Y" range — the high end of the
    // range is less useful at-a-glance than knowing the entry point. Detail
    // shows a single summary fact and preserves "Price unavailable".
    private static func priceRangeLabel(
        from tickets: [Components.Schemas.Ticket]?,
        includeSoldOut: Bool
    ) -> String? {
        let prices = (tickets ?? [])
            .filter { includeSoldOut || $0.soldOut != true }
            .compactMap(\.price)
            .sorted()

        guard let lowestPrice = prices.first else {
            return nil
        }

        guard let highestPrice = prices.last, highestPrice != lowestPrice else {
            return formatPrice(lowestPrice)
        }

        // Multiple tiers. Free entry available → "Free" reads cleaner than
        // "From Free" and matches the user's mental model ("you can get in
        // free"). Otherwise: "From $X".
        if lowestPrice == 0 {
            return "Free"
        }

        return "From \(formatPrice(lowestPrice))"
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

    private static let currencyFormatter: NumberFormatter = {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.locale = Locale(identifier: "en_US")
        formatter.currencyCode = "USD"
        return formatter
    }()
}
