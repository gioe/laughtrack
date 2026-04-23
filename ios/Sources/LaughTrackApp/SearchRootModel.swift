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

        var queryPrompt: String {
            switch self {
            case .shows:
                return "Search comedians appearing in shows"
            case .comedians:
                return "Search comedian names"
            case .clubs:
                return "Search club names"
            }
        }

        var queryHelpText: String {
            switch self {
            case .shows:
                return "Shows search matches comedian names for now. Switch to Clubs to search by venue."
            case .comedians:
                return "Find comedian profiles by name."
            case .clubs:
                return "Find comedy clubs and venue pages by name."
            }
        }
    }

    @Published var query = ""
    @Published var activePivot: Pivot = .shows
    @Published var selectedShortcut: String? = "Near Me"

    struct Seed: Equatable {
        let pivot: Pivot
        let query: String
        let shortcut: String?
    }

    func applySeed(_ seed: Seed) {
        activePivot = seed.pivot
        query = seed.query
        selectedShortcut = seed.shortcut
    }

    func selectShortcut(_ shortcut: String) {
        selectedShortcut = shortcut
        activePivot = .shows
    }

    func applyShortcutFilters(
        to showsModel: ShowsDiscoveryModel,
        now: Date = Date(),
        calendar: Calendar = .current
    ) {
        switch selectedShortcut {
        case "Tonight":
            let start = calendar.startOfDay(for: now)
            showsModel.useDateRange = true
            showsModel.fromDate = start
            showsModel.toDate = calendar.date(byAdding: .day, value: 1, to: start) ?? start
            showsModel.sort = .earliest
        case "This Week":
            let start = calendar.startOfDay(for: now)
            showsModel.useDateRange = true
            showsModel.fromDate = start
            showsModel.toDate = calendar.date(byAdding: .day, value: 7, to: start) ?? start
            showsModel.sort = .earliest
        case "Near Me":
            showsModel.useDateRange = false
            showsModel.sort = .earliest
        default:
            break
        }
    }

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

@MainActor
final class SearchNavigationBridge: ObservableObject {
    struct Request: Identifiable {
        let id = UUID()
        let seed: SearchRootModel.Seed
    }

    @Published private(set) var request: Request?

    func openSearch(_ seed: SearchRootModel.Seed) {
        request = Request(seed: seed)
    }

    func clearRequest(_ consumedRequest: Request) {
        guard request?.id == consumedRequest.id else {
            return
        }

        request = nil
    }
}
