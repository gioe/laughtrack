import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ClubDetailView: View {
    let clubID: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL
    @Environment(\.serviceContainer) private var serviceContainer
    @StateObject private var model: ClubDetailModel
    @State private var feedbackMessage: String?

    init(clubID: Int, apiClient: Client) {
        self.clubID = clubID
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: ClubDetailModel(clubID: clubID))
    }

    var body: some View {
        Group {
            switch model.phase {
            case .idle, .loading:
                CalendarDetailSkeleton()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.reload(apiClient: apiClient) },
                    signIn: { coordinator.push(.profile) }
                )
                .padding()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .success(let content):
                let club = content.club
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                    DetailHero(
                        title: club.name,
                        subtitle: ClubDetailHeroPresentation.subtitle(
                            upcomingShowCount: content.upcomingShows.count,
                            zipCode: club.zipCode
                        ),
                        imageURL: club.imageUrl,
                        badges: [],
                        actions: clubHeroActions(club: club),
                        openURL: { url in
                            openURL(url)
                        }
                    )
                    .ignoresSafeArea(.container, edges: .top)

                    VStack(alignment: .leading, spacing: 20) {
                        ClubShowsSearchSection(
                            clubName: club.name,
                            apiClient: apiClient,
                            nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self)
                        )
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, theme.spacing.lg)
                    }
                }
            }
        }
        .ignoresSafeArea(.container, edges: .top)
        .accessibilityIdentifier(LaughTrackViewTestID.clubDetailScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .modifier(EntityDetailNavigationChrome(entity: .club))
        .task {
            await model.loadIfNeeded(apiClient: apiClient)
        }
        .alert("LaughTrack", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
    }

    private func clubHeroActions(club: Components.Schemas.ClubDetail) -> [DetailHeroAction] {
        [
            DetailHeroAction(
                title: "Website",
                systemImage: "arrow.up.right",
                url: URL.normalizedExternalURL(club.website)
            ),
            DetailHeroAction(
                title: "Maps",
                systemImage: "map.fill",
                url: URL.mapsURL(for: club.address)
            )
        ]
    }
}

enum ClubDetailHeroPresentation {
    static func subtitle(upcomingShowCount: Int, zipCode: String?) -> String? {
        nil
    }
}

private struct ClubShowsSearchSection: View {
    let clubName: String
    let apiClient: Client

    @StateObject private var model: ShowsDiscoveryModel

    init(
        clubName: String,
        apiClient: Client,
        nearbyLocationController: NearbyLocationController
    ) {
        self.clubName = clubName
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: ShowsDiscoveryModel(
            nearbyLocationController: nearbyLocationController,
            pinnedClubName: clubName
        ))
    }

    var body: some View {
        // Club detail inherits the shared SearchToolbar through ShowsDiscoveryView.
        ShowsDiscoveryView(
            apiClient: apiClient,
            model: model
        )
    }
}
