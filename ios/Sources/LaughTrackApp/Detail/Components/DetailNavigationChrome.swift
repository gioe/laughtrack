import SwiftUI

enum DetailNavigationChrome {
    enum Entity {
        case club
        case comedian
        case show
    }

    static let extendsHeroBehindTopSafeArea = true

    static func title(for entity: Entity) -> String {
        switch entity {
        case .club, .comedian:
            return ""
        case .show:
            return "Show"
        }
    }
}

struct EntityDetailNavigationChrome: ViewModifier {
    let entity: DetailNavigationChrome.Entity

    func body(content: Content) -> some View {
        #if os(iOS)
        content
            .navigationTitle(DetailNavigationChrome.title(for: entity))
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
        #else
        content
            .navigationTitle(DetailNavigationChrome.title(for: entity))
        #endif
    }
}
