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
                show.soldOut == true ? "Sold out" : nil,
            ].compactMap { $0 },
            systemImage: "ticket.fill",
            imageURL: Self.artworkImageURL(for: show)
        )
    }

    static func title(for show: Components.Schemas.Show) -> String {
        let name = featuredComedian(for: show)?.name.trimmingCharacters(in: .whitespacesAndNewlines)
        if let name, !name.isEmpty {
            return name
        }

        let showName = show.name?.trimmingCharacters(in: .whitespacesAndNewlines)
        return showName?.isEmpty == false ? showName! : "Untitled show"
    }

    static func artworkImageURL(for show: Components.Schemas.Show) -> String? {
        let imageURL = featuredComedian(for: show)?.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        return imageURL?.isEmpty == false ? imageURL : nil
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
}
