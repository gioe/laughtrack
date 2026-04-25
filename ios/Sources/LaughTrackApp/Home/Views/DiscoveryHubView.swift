import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

private enum DiscoverySection: String, CaseIterable, Identifiable {
    case shows
    case comedians
    case clubs

    var id: String { rawValue }

    var title: String {
        switch self {
        case .shows: return "Shows"
        case .comedians: return "Comedians"
        case .clubs: return "Clubs"
        }
    }

    var subtitle: String {
        switch self {
        case .shows: return "Upcoming dates and ticket links."
        case .comedians: return "Search talent and save favorites."
        case .clubs: return "Browse rooms and venue links."
        }
    }
}

struct DiscoveryHubView: View {
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @State private var selection: DiscoverySection = .shows
    @StateObject private var showsModel: ShowsDiscoveryModel
    @StateObject private var comediansModel = ComediansDiscoveryModel()
    @StateObject private var clubsModel = ClubsDiscoveryModel()

    init(
        apiClient: Client,
        nearbyLocationController: NearbyLocationController
    ) {
        self.apiClient = apiClient
        _showsModel = StateObject(
            wrappedValue: ShowsDiscoveryModel(
                nearbyLocationController: nearbyLocationController
            )
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            LaughTrackCard(tone: .accent) {
                VStack(alignment: .leading, spacing: theme.spacing.lg) {
                    LaughTrackSectionHeader(
                        eyebrow: "Browse",
                        title: selection.title,
                        subtitle: selection.subtitle
                    )

                    Picker("Browse", selection: $selection) {
                        ForEach(DiscoverySection.allCases) { section in
                            Text(section.title).tag(section)
                        }
                    }
                    .pickerStyle(.segmented)

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: theme.spacing.sm) {
                            ForEach(DiscoverySection.allCases) { section in
                                LaughTrackBadge(
                                    section.title,
                                    systemImage: badgeIcon(for: section),
                                    tone: selection == section ? .highlight : .neutral
                                )
                            }
                        }
                    }
                }
            }

            Group {
                switch selection {
                case .shows:
                    ShowsDiscoveryView(apiClient: apiClient, model: showsModel)
                case .comedians:
                    ComediansDiscoveryView(apiClient: apiClient, model: comediansModel)
                case .clubs:
                    ClubsDiscoveryView(apiClient: apiClient, model: clubsModel)
                }
            }
        }
    }

    private func badgeIcon(for section: DiscoverySection) -> String {
        switch section {
        case .shows:
            return "ticket.fill"
        case .comedians:
            return "music.mic"
        case .clubs:
            return "building.2.fill"
        }
    }
}
