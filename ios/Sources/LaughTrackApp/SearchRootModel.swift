import Foundation

@MainActor
protocol SearchRootQueryReceivable: AnyObject {
    func applySearchRootQuery(_ query: String)
}

@MainActor
final class SearchRootModel: ObservableObject {
    enum Pivot: String, CaseIterable, Identifiable {
        case shows
        case comedians
        case clubs

        var id: String { rawValue }
        var title: String { rawValue.capitalized }
    }

    @Published var query = ""
    @Published var activePivot: Pivot = .shows

    func applyQuery(to target: any SearchRootQueryReceivable) {
        target.applySearchRootQuery(query)
    }

    func applyQuery(
        showsModel: ShowsDiscoveryModel,
        comediansModel: ComediansDiscoveryModel,
        clubsModel: ClubsDiscoveryModel
    ) {
        switch activePivot {
        case .shows:
            applyQuery(to: showsModel)
        case .comedians:
            applyQuery(to: comediansModel)
        case .clubs:
            applyQuery(to: clubsModel)
        }
    }
}
