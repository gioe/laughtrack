import Foundation
import LaughTrackAPIClient

enum ShowPricePresentation {
    static func rowPriceLabel(for show: Components.Schemas.Show) -> String? {
        lowestPriceLabel(from: show.tickets, includeSoldOut: false)
    }

    static func rowPreviousPriceLabel(for show: Components.Schemas.Show) -> String? {
        lowestPriceLabel(from: show.tickets, includeSoldOut: true)
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

    // Rows stay compact for scannable lists and expose only the lowest
    // available tier. Detail shows the same summary fact and preserves
    // "Price unavailable".
    private static func lowestPriceLabel(
        from tickets: [Components.Schemas.Ticket]?,
        includeSoldOut: Bool
    ) -> String? {
        let lowestPrice = (tickets ?? [])
            .filter { includeSoldOut || $0.soldOut != true }
            .compactMap(\.price)
            .min()

        guard let lowestPrice else {
            return nil
        }

        return formatPrice(lowestPrice)
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
