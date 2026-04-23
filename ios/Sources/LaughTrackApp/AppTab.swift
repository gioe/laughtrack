import Foundation

enum AppTab: Hashable, CaseIterable {
    case home
    case search
    case activity
    case profile

    var title: String {
        switch self {
        case .home:
            return "Home"
        case .search:
            return "Search"
        case .activity:
            return "Activity"
        case .profile:
            return "Profile"
        }
    }
}
