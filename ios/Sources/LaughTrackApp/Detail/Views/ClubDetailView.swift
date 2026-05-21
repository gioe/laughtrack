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
    @EnvironmentObject private var clubFavorites: ClubFavoriteStore
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
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
                let isFavorite = clubFavorites.value(for: club.id)
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                    DetailHero(
                        title: club.name,
                        imageURL: club.imageUrl,
                        badges: [],
                        actions: clubHeroActions(club: club),
                        openURL: { url in
                            openURL(url)
                        },
                        favoriteState: DetailHeroFavoriteState(
                            isFavorite: isFavorite,
                            isPending: clubFavorites.isPending(club.id),
                            action: {
                                await toggleFavorite(
                                    clubID: club.id,
                                    name: club.name,
                                    currentValue: isFavorite
                                )
                            }
                        ),
                        fallbackSystemImage: "building.2.fill"
                    )
                    .ignoresSafeArea(.container, edges: .top)

                    VStack(alignment: .leading, spacing: 20) {
                        PinnedShowsList(
                            apiClient: apiClient,
                            nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self),
                            pinnedClubName: club.name
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
        .modifier(EntityDetailNavigationChrome(entity: .club, title: navigationTitle))
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
        ClubDetailHeroPresentation.actions(for: club)
    }

    private func toggleFavorite(clubID: Int, name: String, currentValue: Bool) async {
        let result = await clubFavorites.toggle(
            clubID: clubID,
            currentValue: currentValue,
            apiClient: apiClient,
            authManager: authManager
        )

        switch result {
        case .updated(let next):
            feedbackMessage = FavoriteFeedback.message(for: name, isFavorite: next)
        case .signInRequired:
            loginModalPresenter.present()
        case .failure(let message):
            feedbackMessage = message
        }
    }

    private var navigationTitle: String {
        if case .success(let content) = model.phase {
            return content.club.name
        }
        return ""
    }
}

enum ClubDetailHeroPresentation {
    static func actions(for club: Components.Schemas.ClubDetail) -> [DetailHeroAction] {
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

