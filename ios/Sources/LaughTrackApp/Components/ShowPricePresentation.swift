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
            return "Unavailable"
        }

        if lowest <= 0 {
            return "Free"
        }

        return currencyFormatter.string(from: NSNumber(value: lowest)) ?? "$\(lowest)"
    }

    // Rows stay compact for scannable lists and expose ranges/strikethrough
    // context. Detail shows a single summary fact and preserves Unavailable.
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

        if lowestPrice == 0 {
            return "Free - \(formatPrice(highestPrice))"
        }

        return "\(formatPrice(lowestPrice)) - \(formatPrice(highestPrice))"
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
