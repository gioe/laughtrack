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
        if detailIsSoldOut(for: show) {
            return "Sold out"
        }

        guard detailTicketURL(for: show) != nil else {
            return "Ticket link unavailable"
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

    static func detailIsSoldOut(for show: Components.Schemas.ShowDetail) -> Bool {
        let tickets = show.tickets ?? []
        // Older API responses used isSoldOut for a missing destination too.
        // Without a CTA URL, inventory fields provide the trustworthy signal.
        return show.soldOut == true
            || (!tickets.isEmpty && tickets.allSatisfy { $0.soldOut == true })
            || (show.cta.isSoldOut && ticketURL(show.cta.url) != nil)
    }

    static func detailTicketURL(for show: Components.Schemas.ShowDetail) -> URL? {
        guard !detailIsSoldOut(for: show) else { return nil }
        let availableTicketURL = (show.tickets ?? [])
            .filter { $0.soldOut != true }
            .compactMap { ticketURL($0.purchaseUrl) }
            .first
        return availableTicketURL ?? ticketURL(show.cta.url) ?? ticketURL(show.showPageUrl)
    }

    static func detailTicketExplanation(_ summary: String) -> String? {
        switch summary {
        case "Ticket link unavailable":
            return "A ticket or event page link is not available. This does not mean the show is sold out."
        case "Price unavailable":
            return priceUnavailableExplanation
        default:
            return nil
        }
    }

    private static func ticketURL(_ rawValue: String?) -> URL? {
        guard let rawValue else { return nil }
        let value = rawValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty,
              value.rangeOfCharacter(from: .whitespacesAndNewlines.union(.controlCharacters)) == nil,
              let url = URL.normalizedExternalURL(value),
              let scheme = url.scheme?.lowercased(),
              scheme == "http" || scheme == "https",
              let host = url.host, !host.isEmpty else { return nil }
        if !value.hasPrefix("/"), URL(string: value)?.scheme == nil, !host.contains(".") {
            return nil
        }
        return url
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
