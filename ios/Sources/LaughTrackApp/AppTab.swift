import Foundation

enum AppTab: Hashable, CaseIterable {
    case nearMe
    case search
    case favorites

    var title: String {
        switch self {
        case .nearMe:
            return "Near Me"
        case .search:
            return "Search"
        case .favorites:
            return "Favorites"
        }
    }
}
