import SwiftUI
import LaughTrackBridge

struct HomeSearchEntryCard: View {
    let pivot: SearchRootModel.Pivot
    let title: String
    let subtitle: String
    let metadata: [String]
    let systemImage: String
    let shortcut: String?
    let testID: String
    let searchNavigationBridge: SearchNavigationBridge

    var body: some View {
        Button {
            searchNavigationBridge.openSearch(.init(pivot: pivot, query: "", shortcut: shortcut))
        } label: {
            LaughTrackResultRow(
                title: title,
                subtitle: subtitle,
                metadata: metadata,
                systemImage: systemImage,
                accessoryTitle: "Search"
            )
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier(testID)
    }
}

struct HomeSearchEntryCardConfig {
    let pivot: SearchRootModel.Pivot
    let title: String
    let subtitle: String
    let metadata: [String]
    let systemImage: String
    let shortcut: String?
    let testID: String

    static let shows = HomeSearchEntryCardConfig(
        pivot: .shows,
        title: "Shows",
        subtitle: "Local dates first",
        metadata: ["Near Me ready", "One search surface"],
        systemImage: "magnifyingglass",
        shortcut: "Near Me",
        testID: LaughTrackViewTestID.homeShowsSearchButton
    )

    static let clubs = HomeSearchEntryCardConfig(
        pivot: .clubs,
        title: "Clubs",
        subtitle: "Venue pages and lineups",
        metadata: ["Tonight-ready", "Upcoming bills"],
        systemImage: "building.2",
        shortcut: nil,
        testID: LaughTrackViewTestID.homeClubsSearchButton
    )

    static let comedians = HomeSearchEntryCardConfig(
        pivot: .comedians,
        title: "Comedians",
        subtitle: "Profiles and favorites",
        metadata: ["Follow a comic", "See where they're next"],
        systemImage: "music.mic",
        shortcut: nil,
        testID: LaughTrackViewTestID.homeComediansSearchButton
    )
}

extension HomeSearchEntryCard {
    init(config: HomeSearchEntryCardConfig, searchNavigationBridge: SearchNavigationBridge) {
        self.pivot = config.pivot
        self.title = config.title
        self.subtitle = config.subtitle
        self.metadata = config.metadata
        self.systemImage = config.systemImage
        self.shortcut = config.shortcut
        self.testID = config.testID
        self.searchNavigationBridge = searchNavigationBridge
    }
}
