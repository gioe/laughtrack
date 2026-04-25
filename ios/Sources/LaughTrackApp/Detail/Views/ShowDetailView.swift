import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ShowDetailView: View {
    let showID: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL

    @StateObject private var model: ShowDetailModel
    @State private var feedbackMessage: String?

    init(showID: Int, apiClient: Client) {
        self.showID = showID
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: ShowDetailModel(showID: showID))
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
                    retry: { await model.reload(apiClient: apiClient, favorites: favorites) },
                    signIn: { coordinator.push(.settings) }
                )
                .padding()
            case .success(let response):
                let show = response.data
                VStack(alignment: .leading, spacing: 20) {
                    DetailHero(
                        title: show.name ?? "Untitled show",
                        subtitle: ShowFormatting.detailDate(show.date, timezoneID: show.timezone),
                        imageURL: show.imageUrl,
                        badges: showHeroBadges(show: show)
                    )

                    if let address = show.address ?? show.club.address {
                        DetailInfoCard(eyebrow: "Venue", title: show.club.name, subtitle: "Tap this card to open the full club detail.", rows: [
                            DetailInfoRow(label: "Address", value: address),
                            DetailInfoRow(label: "Room", value: show.room),
                            DetailInfoRow(label: "Distance", value: ShowFormatting.distance(show.distanceMiles))
                        ])
                        .onTapGesture {
                            coordinator.open(.club(show.club.id))
                        }
                    }

                    if let description = show.description, !description.isEmpty {
                        DetailTextCard(eyebrow: "Editor’s note", title: "About this show", text: description)
                    }

                    ShowCTASection(show: show) { url in
                        openURL(url)
                    }

                    ShowLineupSection(
                        lineup: show.lineup ?? [],
                        apiClient: apiClient,
                        feedbackMessage: $feedbackMessage
                    ) { comedian in
                        coordinator.open(.comedian(comedian.id))
                    }

                    RelatedShowsSection(relatedShows: response.relatedShows) { related in
                        coordinator.open(.show(related.id))
                    }
                }
                .padding()
            }
        }
        .accessibilityIdentifier(LaughTrackViewTestID.showDetailScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Show")
        .modifier(InlineNavigationTitle())
        .task {
            await model.loadIfNeeded(apiClient: apiClient, favorites: favorites)
        }
        .alert("LaughTrack", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
    }

    private func showHeroBadges(show: Components.Schemas.ShowDetail) -> [DetailHeroBadge] {
        var badges = [
            DetailHeroBadge(
                title: show.club.name,
                systemImage: "building.2.fill",
                tone: .highlight
            )
        ]

        if let distance = ShowFormatting.distance(show.distanceMiles) {
            badges.append(
                DetailHeroBadge(
                    title: distance,
                    systemImage: "location.fill",
                    tone: .neutral
                )
            )
        }

        if show.soldOut == true {
            badges.append(
                DetailHeroBadge(
                    title: "Sold out",
                    systemImage: "ticket.fill",
                    tone: .warning
                )
            )
        }

        return badges
    }
}

private struct ShowLineupSection: View {
    let lineup: [Components.Schemas.ComedianLineup]
    let apiClient: Client
    @Binding var feedbackMessage: String?
    let openDetail: (Components.Schemas.ComedianLineup) -> Void

    var body: some View {
        LaughTrackCard {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(
                    eyebrow: "Lineup",
                    title: "Tonight’s bill",
                    subtitle: "Tap a comic to see their upcoming shows."
                )

                if lineup.isEmpty {
                    EmptyCard(message: "Lineup details are not available yet.")
                } else {
                    ForEach(lineup, id: \.uuid) { comedian in
                        ComedianLineupRow(
                            comedian: comedian,
                            apiClient: apiClient,
                            feedbackMessage: $feedbackMessage,
                            openDetail: { openDetail(comedian) }
                        )
                    }
                }
            }
        }
    }
}

private struct RelatedShowsSection: View {
    let relatedShows: [Components.Schemas.Show]
    let openDetail: (Components.Schemas.Show) -> Void

    var body: some View {
        LaughTrackCard(tone: .muted) {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(
                    eyebrow: "Keep browsing",
                    title: "Related shows",
                    subtitle: "More shows you might like."
                )

                if relatedShows.isEmpty {
                    EmptyCard(message: "No related shows are available yet.")
                } else {
                    ForEach(relatedShows, id: \.id) { related in
                        Button {
                            openDetail(related)
                        } label: {
                            ShowRow(show: related)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }
}

private struct ShowCTASection: View {
    @Environment(\.appTheme) private var theme

    let show: Components.Schemas.ShowDetail
    let openURL: (URL) -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let primaryURL = URL.normalizedExternalURL(show.cta.url) ?? URL.normalizedExternalURL(show.showPageUrl)
        let fallbackURL = URL.normalizedExternalURL(show.showPageUrl)

        LaughTrackCard(tone: show.cta.isSoldOut ? .muted : .accent) {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(
                    eyebrow: "Tickets",
                    title: show.cta.isSoldOut ? "Join the wait for the next one" : "Secure your seat",
                    subtitle: show.cta.isSoldOut ? "This show is marked sold out, but the venue path still stays visible." : "Primary and fallback buttons use the same branded language as the rest of LaughTrack."
                )

                if let primaryURL {
                    LaughTrackButton(
                        show.cta.label,
                        systemImage: "arrow.up.right",
                        tone: show.cta.isSoldOut ? .secondary : .primary
                    ) {
                        openURL(primaryURL)
                    }
                    .disabled(show.cta.isSoldOut)
                } else {
                    EmptyCard(message: "Tickets are not linked yet for this show.")
                }

                if let fallbackURL, primaryURL != fallbackURL {
                    LaughTrackButton("Open show page", systemImage: "safari", tone: .tertiary) {
                        openURL(fallbackURL)
                    }
                }

                if let tickets = show.tickets, !tickets.isEmpty {
                    VStack(spacing: 10) {
                        ForEach(Array(tickets.enumerated()), id: \.offset) { index, ticket in
                            LaughTrackCard {
                                HStack {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(ticket._type ?? "Ticket option \(index + 1)")
                                            .font(laughTrack.typography.action)
                                            .foregroundStyle(laughTrack.colors.textPrimary)
                                        if let price = ticket.price {
                                            Text(price, format: .currency(code: "USD"))
                                                .font(laughTrack.typography.metadata)
                                                .foregroundStyle(laughTrack.colors.textSecondary)
                                        }
                                    }
                                    Spacer()
                                    if let url = URL.normalizedExternalURL(ticket.purchaseUrl) {
                                        LaughTrackButton(
                                            ticket.soldOut == true ? "Sold out" : "Open",
                                            systemImage: ticket.soldOut == true ? "xmark.circle" : "arrow.up.right",
                                            tone: ticket.soldOut == true ? .secondary : .tertiary,
                                            fullWidth: false
                                        ) {
                                            openURL(url)
                                        }
                                        .disabled(ticket.soldOut == true)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
