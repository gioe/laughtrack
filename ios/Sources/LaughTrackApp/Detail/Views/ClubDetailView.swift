import SwiftUI
import MapKit
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
    @State private var safariURL: URL?
    @State private var selectedDates: Set<Date> = []

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
                            ExternalLinkRouter.route(url, presentedURL: $safariURL, openURL: openURL)
                        }
                    )
                    .ignoresSafeArea(.container, edges: .top)

                    if #available(iOS 17.0, macOS 14.0, *), let coordinate = club.coordinate {
                        ClubMapSection(
                            clubName: club.name,
                            address: club.address,
                            coordinate: coordinate
                        )
                        .padding(.horizontal, theme.spacing.lg * 2)
                        .padding(.top, theme.spacing.lg)
                    }

                    VStack(alignment: .leading, spacing: 20) {
                        LaughTrackCard(density: .tight) {
                            VStack(alignment: .leading, spacing: 12) {
                                LaughTrackSectionHeader(title: "Upcoming shows")

                                ShowsCalendarSection(
                                    shows: content.upcomingShows,
                                    onSelectShow: { showID in coordinator.open(.show(showID)) },
                                    selectedDates: $selectedDates,
                                    jumpToDate: Binding(
                                        get: { model.fromDate },
                                        set: { newDate in
                                            model.fromDate = newDate
                                            Task { await model.refreshUpcomingShows(apiClient: apiClient) }
                                        }
                                    ),
                                    isRefreshing: model.isRefetchingShows,
                                    thumbnailImageURL: { show in
                                        ShowRow.artworkImageURL(for: show) ?? show.imageUrl
                                    }
                                )
                            }
                        }
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, theme.spacing.lg)
                    }
                }
                .safariSheet(url: $safariURL)
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
        var actions: [DetailHeroAction] = [
            DetailHeroAction(
                title: "Website",
                systemImage: "arrow.up.right",
                url: URL.normalizedExternalURL(club.website)
            )
        ]
        let hasCoordinate: Bool
        if #available(iOS 17.0, macOS 14.0, *) {
            hasCoordinate = club.coordinate != nil
        } else {
            hasCoordinate = false
        }
        if !hasCoordinate {
            actions.append(
                DetailHeroAction(
                    title: "Maps",
                    systemImage: "map.fill",
                    url: URL.mapsURL(for: club.address)
                )
            )
        }
        return actions
    }
}

private extension Components.Schemas.ClubDetail {
    var coordinate: CLLocationCoordinate2D? {
        guard let lat = self.latitude, let lon = self.longitude else { return nil }
        return CLLocationCoordinate2D(latitude: lat, longitude: lon)
    }
}

@available(iOS 17.0, macOS 14.0, *)
private struct ClubMapSection: View {
    let clubName: String
    let address: String
    let coordinate: CLLocationCoordinate2D

    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL
    @State private var cameraPosition: MapCameraPosition

    init(clubName: String, address: String, coordinate: CLLocationCoordinate2D) {
        self.clubName = clubName
        self.address = address
        self.coordinate = coordinate
        _cameraPosition = State(initialValue: .region(MKCoordinateRegion(
            center: coordinate,
            span: MKCoordinateSpan(latitudeDelta: 0.005, longitudeDelta: 0.005)
        )))
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack(alignment: .topTrailing) {
            Map(position: $cameraPosition, interactionModes: [.pan, .zoom]) {
                Marker(clubName, coordinate: coordinate)
                    .tint(laughTrack.colors.accent)
            }
            .frame(height: 220)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))

            Button {
                if let url = URL.mapsURL(for: address) {
                    openURL(url)
                }
            } label: {
                Label("Open in Maps", systemImage: "arrow.up.right.square.fill")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(.ultraThinMaterial, in: Capsule())
            }
            .padding(8)
            .accessibilityLabel("Open \(clubName) in Maps")
        }
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
        ShowsDiscoveryView(
            apiClient: apiClient,
            model: model
        )
    }
}
