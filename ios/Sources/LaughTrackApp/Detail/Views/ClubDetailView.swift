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
    @StateObject private var model: ClubDetailModel
    @State private var feedbackMessage: String?

    init(clubID: Int, apiClient: Client) {
        self.clubID = clubID
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: ClubDetailModel(clubID: clubID))
    }

    var body: some View {
        ScrollView {
            switch model.phase {
            case .idle, .loading:
                LoadingCard()
                    .padding()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.reload(apiClient: apiClient) },
                    signIn: { coordinator.push(.settings) }
                )
                .padding()
            case .success(let content):
                let club = content.club
                VStack(alignment: .leading, spacing: 20) {
                    DetailHero(
                        title: club.name,
                        subtitle: content.upcomingShows.isEmpty ? (club.zipCode ?? "Club detail") : "\(content.upcomingShows.count) upcoming show\(content.upcomingShows.count == 1 ? "" : "s")",
                        imageURL: club.imageUrl,
                        badges: clubHeroBadges(club: club, upcomingShowCount: content.upcomingShows.count, featuredComedianCount: content.featuredComedians.count)
                    )

                    DetailInfoCard(eyebrow: "Club details", title: "Venue", subtitle: "Core contact information comes directly from the club.", rows: [
                        DetailInfoRow(label: "Address", value: club.address),
                        DetailInfoRow(label: "ZIP", value: club.zipCode),
                        DetailInfoRow(label: "Phone", value: club.phoneNumber)
                    ])

                    DetailLinkCard(
                        eyebrow: "Actions",
                        title: "Take the next step",
                        subtitle: "Jump out to the venue’s website, maps, or phone line when that data is available.",
                        links: clubActionLinks(club: club),
                        openURL: { url in openURL(url) }
                    )

                    LaughTrackCard {
                        VStack(alignment: .leading, spacing: 12) {
                            LaughTrackSectionHeader(
                                eyebrow: "Upcoming shows",
                                title: "What’s on at this room",
                                subtitle: "Shows are filtered to this club so you can jump straight into a date."
                            )

                            if let relatedContentMessage = content.relatedContentMessage {
                                InlineStatusMessage(message: relatedContentMessage)
                            }

                            if content.upcomingShows.isEmpty {
                                EmptyCard(message: "No upcoming shows are available for this club right now.")
                            } else {
                                ForEach(content.upcomingShows, id: \.id) { show in
                                    Button {
                                        coordinator.open(.show(show.id))
                                    } label: {
                                        ShowRow(show: show)
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }
                    }

                    LaughTrackCard(tone: .muted) {
                        VStack(alignment: .leading, spacing: 12) {
                            LaughTrackSectionHeader(
                                eyebrow: "Featured comedians",
                                title: "Artists on upcoming bills",
                                subtitle: "When lineup data is available, you can move straight from the club profile into comedian details."
                            )

                            if content.featuredComedians.isEmpty {
                                EmptyCard(message: "No featured comedians are available for this club yet.")
                            } else {
                                ForEach(content.featuredComedians, id: \.uuid) { comedian in
                                    ComedianLineupRow(
                                        comedian: comedian,
                                        apiClient: apiClient,
                                        feedbackMessage: $feedbackMessage,
                                        openDetail: { coordinator.open(.comedian(comedian.id)) }
                                    )
                                }
                            }
                        }
                    }
                }
                .padding()
            }
        }
        .accessibilityIdentifier(LaughTrackViewTestID.clubDetailScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Club")
        .modifier(InlineNavigationTitle())
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

    private func clubHeroBadges(
        club: Components.Schemas.ClubDetail,
        upcomingShowCount: Int,
        featuredComedianCount: Int
    ) -> [DetailHeroBadge] {
        var badges = [DetailHeroBadge(title: "Club detail", systemImage: "building.2.fill", tone: .highlight)]

        if upcomingShowCount > 0 {
            badges.append(
                DetailHeroBadge(
                    title: "\(upcomingShowCount) upcoming",
                    systemImage: "calendar",
                    tone: .neutral
                )
            )
        }

        if featuredComedianCount > 0 {
            badges.append(
                DetailHeroBadge(
                    title: "\(featuredComedianCount) comics",
                    systemImage: "music.mic",
                    tone: .accent
                )
            )
        }

        if !club.address.isEmpty {
            badges.append(
                DetailHeroBadge(
                    title: "Address on file",
                    systemImage: "mappin.and.ellipse",
                    tone: .neutral
                )
            )
        }

        if let phoneNumber = club.phoneNumber, !phoneNumber.isEmpty {
            badges.append(
                DetailHeroBadge(
                    title: "Call venue",
                    systemImage: "phone.fill",
                    tone: .accent
                )
            )
        }

        return badges
    }

    private func clubActionLinks(club: Components.Schemas.ClubDetail) -> [DetailLink] {
        [
            DetailLink(title: "Visit website", url: URL.normalizedExternalURL(club.website)),
            DetailLink(title: "Open in Maps", url: URL.mapsURL(for: club.address)),
            DetailLink(title: "Call venue", url: URL.phoneURL(club.phoneNumber))
        ]
    }
}
