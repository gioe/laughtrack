import Foundation

enum AppTab: Hashable, CaseIterable {
    case home
    case search
    case library
    case profile

    var title: String {
        switch self {
        case .home:
            return "Home"
        case .search:
            return "Search"
        case .library:
            return "Library"
        case .profile:
            return "Profile"
        }
    }
}
