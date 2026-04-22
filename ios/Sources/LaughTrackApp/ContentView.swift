import SwiftUI
import LaughTrackBridge

struct ContentView: View {
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme

    var body: some View {
        CoordinatedNavigationStack(coordinator: coordinator) { route in
            switch route {
            case .home:
                HomeView()
            case .settings:
                SettingsView()
            }
        } root: {
            HomeView()
        }
        .tint(theme.colors.primary)
    }
}

struct HomeView: View {
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme

    private let content = HomeContent.sample

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: laughTrack.spacing.sectionGap) {
                HomeHeroSection(content: content.hero, openSettings: openSettings)
                PerformerSection(
                    title: "Trending Comedians",
                    subtitle: "Catch the comedians everyone is talking about.",
                    performers: content.performers
                )
                PerformerSection(
                    title: "Comedians Near You",
                    subtitle: "The comics worth tracking first when you want a nearby night out.",
                    performers: content.nearYouPerformers
                )
                ShowRailSection(title: "Shows Tonight", subtitle: "Live comedy happening right now, near you", shows: content.tonightShows)
                ShowRailSection(title: "More Near You", subtitle: "Upcoming shows at clubs in your area", shows: content.nearbyShows)
                ShowRailSection(title: "Trending This Week", subtitle: "The most popular shows happening in the next 7 days", shows: content.trendingShows)
                ClubRailSection(clubs: content.clubs)
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.top, laughTrack.spacing.heroPadding * 0.72)
            .padding(.bottom, laughTrack.spacing.heroPadding)
        }
        .background(laughTrack.colors.canvas.ignoresSafeArea())
        .background(
            ZStack(alignment: .top) {
                laughTrack.gradients.heroWash
                    .frame(height: 330)
                    .ignoresSafeArea(edges: .top)

                Circle()
                    .fill(laughTrack.colors.accentMuted.opacity(0.35))
                    .frame(width: 280, height: 280)
                    .blur(radius: 32)
                    .offset(x: 120, y: -110)

                Circle()
                    .fill(laughTrack.colors.highlight.opacity(0.18))
                    .frame(width: 220, height: 220)
                    .blur(radius: 24)
                    .offset(x: -120, y: -70)
            },
            alignment: .top
        )
        .navigationTitle("LaughTrack")
        .toolbar {
            ToolbarItem(placement: settingsToolbarPlacement) {
                Button(action: openSettings) {
                    Image(systemName: "slider.horizontal.3")
                        .font(.system(size: theme.iconSizes.md, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.textPrimary)
                }
                .accessibilityLabel("Open settings")
            }
        }
        .modifier(LaughTrackInlineNavigationTitle())
        .modifier(LaughTrackNavigationChrome(background: laughTrack.colors.canvas))
    }

    private func openSettings() {
        withAnimation(theme.laughTrackTokens.motion.tapFeedback) {
            coordinator.push(.settings)
        }
    }
}

struct SettingsView: View {
    @Environment(\.appTheme) private var theme

    @State private var notifyOnDrops = true
    @State private var preferNearbyShows = true
    @State private var hapticsEnabled = true

    private let content = HomeContent.sample

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: laughTrack.spacing.sectionGap) {
                SettingsHeroCard()

                SettingsSectionCard(title: "Discovery") {
                    SettingsToggleRow(
                        title: "Nearby show alerts",
                        subtitle: "Keep the app focused on live sets happening close to you.",
                        isOn: $preferNearbyShows
                    )
                    Divider().overlay(laughTrack.colors.borderSubtle)
                    SettingsToggleRow(
                        title: "Lineup drops",
                        subtitle: "Notify me when trending comedians land new dates.",
                        isOn: $notifyOnDrops
                    )
                }

                SettingsSectionCard(title: "Experience") {
                    SettingsKeyValueRow(
                        title: "Brand voice",
                        value: "Warm canvas, cedar, copper"
                    )
                    Divider().overlay(laughTrack.colors.borderSubtle)
                    SettingsKeyValueRow(
                        title: "Default browsing mode",
                        value: "Shows near you"
                    )
                    Divider().overlay(laughTrack.colors.borderSubtle)
                    SettingsToggleRow(
                        title: "Haptics",
                        subtitle: "Keep taps and saves feeling crisp and intentional.",
                        isOn: $hapticsEnabled
                    )
                }

                SettingsSectionCard(title: "Palette") {
                    HStack(spacing: laughTrack.spacing.itemGap) {
                        ForEach(content.palette, id: \.name) { swatch in
                            PaletteSwatch(swatch: swatch)
                        }
                    }
                }

                SettingsSectionCard(title: "Product notes") {
                    VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                        SettingsBullet(text: "Make discovery feel editorial, not transactional.")
                        SettingsBullet(text: "Keep the hero dramatic and the cards warm.")
                        SettingsBullet(text: "Use sections that match web rhythm: hero, talent, shows, clubs.")
                    }
                }
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.top, laughTrack.spacing.heroPadding * 0.65)
            .padding(.bottom, laughTrack.spacing.heroPadding)
        }
        .background(laughTrack.colors.canvas.ignoresSafeArea())
        .navigationTitle("Settings")
        .modifier(LaughTrackInlineNavigationTitle())
        .modifier(LaughTrackNavigationChrome(background: laughTrack.colors.canvas))
    }
}

#if os(iOS)
private let settingsToolbarPlacement: ToolbarItemPlacement = .topBarTrailing
#else
private let settingsToolbarPlacement: ToolbarItemPlacement = .automatic
#endif

private struct HomeHeroSection: View {
    @Environment(\.appTheme) private var theme

    let content: HomeHeroContent
    let openSettings: () -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: laughTrack.radius.heroPanel, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            laughTrack.colors.heroStart,
                            laughTrack.colors.heroEnd,
                            laughTrack.colors.accentStrong.opacity(0.84),
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )

            Circle()
                .fill(laughTrack.colors.accentMuted.opacity(0.35))
                .frame(width: 190, height: 190)
                .blur(radius: 10)
                .offset(x: 185, y: -15)

            VStack(alignment: .leading, spacing: laughTrack.spacing.clusterGap) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    Text(content.eyebrow)
                        .font(laughTrack.typography.eyebrow)
                        .foregroundStyle(laughTrack.colors.accentMuted)
                        .textCase(.uppercase)
                    Text(content.title)
                        .font(laughTrack.typography.hero)
                        .foregroundStyle(laughTrack.colors.textInverse)
                    Text(content.subtitle)
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textInverse.opacity(0.9))
                        .fixedSize(horizontal: false, vertical: true)
                }

                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    HStack(spacing: laughTrack.spacing.itemGap) {
                        HeroPill(label: content.pills[0], systemImage: "location.fill")
                        HeroPill(label: content.pills[1], systemImage: "sparkles")
                    }
                    HStack(spacing: laughTrack.spacing.itemGap) {
                        ForEach(content.featuredFacts, id: \.self) { fact in
                            Label(fact, systemImage: "smallcircle.fill.circle")
                                .font(laughTrack.typography.metadata)
                                .foregroundStyle(laughTrack.colors.textInverse.opacity(0.86))
                        }
                    }
                }

                HStack(spacing: laughTrack.spacing.itemGap) {
                    ForEach(content.momentCards, id: \.title) { card in
                        HeroMomentCard(card: card)
                    }
                }

                Button(action: openSettings) {
                    HStack(spacing: laughTrack.spacing.itemGap) {
                        Image(systemName: "slider.horizontal.3")
                        Text("Tune your comedy radar")
                    }
                    .font(laughTrack.typography.action)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .padding(.horizontal, laughTrack.spacing.cardPadding)
                    .padding(.vertical, theme.spacing.md)
                    .background(laughTrack.colors.surfaceElevated)
                    .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous))
                }
                .buttonStyle(.plain)
            }
            .padding(laughTrack.spacing.heroPadding * 0.75)
        }
        .shadowStyle(laughTrack.shadows.hero)
    }
}

private struct PerformerSection: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let subtitle: String
    let performers: [FeaturedPerformer]

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.clusterGap) {
            SectionHeader(title: title, subtitle: subtitle)

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: laughTrack.spacing.clusterGap) {
                ForEach(performers, id: \.name) { performer in
                    PerformerCard(performer: performer)
                }
            }
        }
    }
}

private struct ShowRailSection: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let subtitle: String
    let shows: [FeaturedShow]

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.clusterGap) {
            SectionHeader(title: title, subtitle: subtitle)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: laughTrack.spacing.itemGap) {
                    ForEach(shows, id: \.title) { show in
                        ShowCard(show: show)
                    }
                }
                .padding(.trailing, theme.spacing.sm)
            }
        }
    }
}

private struct ClubRailSection: View {
    @Environment(\.appTheme) private var theme

    let clubs: [FeaturedClub]

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.clusterGap) {
            SectionHeader(
                title: "Popular Clubs",
                subtitle: "Comedy venues that already feel like part of the LaughTrack world."
            )

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: laughTrack.spacing.itemGap) {
                    ForEach(clubs, id: \.name) { club in
                        ClubCard(club: club)
                    }
                }
                .padding(.trailing, theme.spacing.sm)
            }
        }
    }
}

private struct SettingsHeroCard: View {
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            Text("Native direction")
                .font(laughTrack.typography.eyebrow)
                .foregroundStyle(laughTrack.colors.accentMuted)
                .textCase(.uppercase)
            Text("Keep the mobile app aligned with the web finish.")
                .font(laughTrack.typography.screenTitle)
                .foregroundStyle(laughTrack.colors.textInverse)
            Text("Settings should reinforce the same palette, hierarchy, and tone that make LaughTrack feel distinct on the web.")
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textInverse.opacity(0.88))
        }
        .padding(laughTrack.spacing.heroPadding * 0.72)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            LinearGradient(
                colors: [
                    laughTrack.colors.heroStart,
                    laughTrack.colors.heroEnd,
                    laughTrack.colors.accentStrong,
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.heroPanel, style: .continuous))
        .shadowStyle(laughTrack.shadows.hero)
    }
}

private struct SettingsSectionCard<Content: View>: View {
    @Environment(\.appTheme) private var theme

    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.clusterGap) {
            Text(title)
                .font(laughTrack.typography.cardTitle)
                .foregroundStyle(laughTrack.colors.textPrimary)

            content
        }
        .padding(laughTrack.spacing.cardPadding)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(laughTrack.colors.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .shadowStyle(laughTrack.shadows.card)
    }
}

private struct SettingsToggleRow: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let subtitle: String
    @Binding var isOn: Bool

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            HStack {
                VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                    Text(title)
                        .font(laughTrack.typography.bodyEmphasis)
                        .foregroundStyle(laughTrack.colors.textPrimary)
                    Text(subtitle)
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                }
                Spacer(minLength: laughTrack.spacing.itemGap)
                Toggle("", isOn: $isOn)
                    .labelsHidden()
                    .tint(laughTrack.colors.accent)
            }
        }
    }
}

private struct SettingsKeyValueRow: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let value: String

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(alignment: .firstTextBaseline) {
            Text(title)
                .font(laughTrack.typography.bodyEmphasis)
                .foregroundStyle(laughTrack.colors.textPrimary)
            Spacer()
            Text(value)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .multilineTextAlignment(.trailing)
        }
    }
}

private struct SettingsBullet: View {
    @Environment(\.appTheme) private var theme

    let text: String

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(alignment: .top, spacing: laughTrack.spacing.itemGap) {
            Circle()
                .fill(laughTrack.colors.accent)
                .frame(width: 8, height: 8)
                .padding(.top, 6)
            Text(text)
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textSecondary)
        }
    }
}

private struct PaletteSwatch: View {
    @Environment(\.appTheme) private var theme

    let swatch: PaletteItem

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            RoundedRectangle(cornerRadius: laughTrack.radius.chip, style: .continuous)
                .fill(swatch.color)
                .frame(height: 72)
                .overlay(
                    RoundedRectangle(cornerRadius: laughTrack.radius.chip, style: .continuous)
                        .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                )

            Text(swatch.name)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textPrimary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct HeroPill: View {
    @Environment(\.appTheme) private var theme

    let label: String
    let systemImage: String

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Label(label, systemImage: systemImage)
            .font(laughTrack.typography.metadata)
            .foregroundStyle(laughTrack.colors.textInverse)
            .padding(.horizontal, theme.spacing.md)
            .padding(.vertical, theme.spacing.sm)
            .background(laughTrack.colors.textInverse.opacity(0.14))
            .clipShape(Capsule())
    }
}

private struct HeroMomentCard: View {
    @Environment(\.appTheme) private var theme

    let card: HeroMomentCardContent

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
            Text(card.kicker)
                .font(laughTrack.typography.eyebrow)
                .foregroundStyle(laughTrack.colors.accentMuted)
            Text(card.title)
                .font(laughTrack.typography.bodyEmphasis)
                .foregroundStyle(laughTrack.colors.textInverse)
            Text(card.detail)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textInverse.opacity(0.8))
        }
        .padding(theme.spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(laughTrack.colors.textInverse.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
    }
}

private struct SectionHeader: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let subtitle: String

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
            Text(title)
                .font(laughTrack.typography.sectionTitle)
                .foregroundStyle(laughTrack.colors.textPrimary)
            Text(subtitle)
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textSecondary)
        }
    }
}

private struct PerformerCard: View {
    @Environment(\.appTheme) private var theme

    let performer: FeaturedPerformer

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .center, spacing: laughTrack.spacing.itemGap) {
            ZStack(alignment: .bottom) {
                Circle()
                    .fill(performer.primaryColor.opacity(0.16))
                    .frame(width: 136, height: 136)

                Circle()
                    .fill(
                        LinearGradient(
                            colors: [
                                performer.primaryColor.opacity(0.92),
                                performer.secondaryColor.opacity(0.85),
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 122, height: 122)

                Text(performer.initials)
                    .font(.system(size: 32, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.white.opacity(0.96))
            }

            VStack(spacing: laughTrack.spacing.tight) {
                Text(performer.name)
                    .font(laughTrack.typography.cardTitle)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .multilineTextAlignment(.center)
                Text(performer.note)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .multilineTextAlignment(.center)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(laughTrack.spacing.cardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .shadowStyle(laughTrack.shadows.card)
    }
}

private struct ShowCard: View {
    @Environment(\.appTheme) private var theme

    let show: FeaturedShow

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            HStack(alignment: .top) {
                Circle()
                    .fill(laughTrack.colors.surfaceMuted)
                    .frame(width: 42, height: 42)
                    .overlay(
                        Image(systemName: "theatermasks.fill")
                            .foregroundStyle(laughTrack.colors.accentStrong)
                    )
                Spacer()
                Text(show.price)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }

            VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                Text(show.venue)
                    .font(laughTrack.typography.bodyEmphasis)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                Text(show.title)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                Text(show.date)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                Text(show.location)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
                Text(show.lineup)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(laughTrack.spacing.cardPadding)
        .frame(width: 280, alignment: .leading)
        .background(laughTrack.colors.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .shadowStyle(laughTrack.shadows.card)
    }
}

private struct ClubCard: View {
    @Environment(\.appTheme) private var theme

    let club: FeaturedClub

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [club.primaryColor, club.secondaryColor],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .frame(height: 142)
                .overlay(
                    VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                        Spacer()
                        Text(club.badge)
                            .font(laughTrack.typography.eyebrow)
                            .foregroundStyle(Color.white.opacity(0.78))
                            .textCase(.uppercase)
                        Text(club.name)
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(Color.white)
                    }
                    .padding(laughTrack.spacing.cardPadding),
                    alignment: .bottomLeading
                )

            Text(club.note)
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textPrimary)

            Text(club.meta)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textSecondary)
        }
        .padding(laughTrack.spacing.cardPadding)
        .frame(width: 246, alignment: .leading)
        .background(laughTrack.colors.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .shadowStyle(laughTrack.shadows.card)
    }
}

private struct HomeContent {
    let hero: HomeHeroContent
    let performers: [FeaturedPerformer]
    let nearYouPerformers: [FeaturedPerformer]
    let tonightShows: [FeaturedShow]
    let nearbyShows: [FeaturedShow]
    let trendingShows: [FeaturedShow]
    let clubs: [FeaturedClub]
    let palette: [PaletteItem]

    static let sample = HomeContent(
        hero: .init(
            eyebrow: "Live comedy near you",
            title: "The easiest way to find a great comedy show tonight.",
            subtitle: "Track the comedians people are already talking about, see what is happening nearby, and jump straight into the clubs shaping your next night out.",
            pills: ["5 miles around you", "Trending this week"],
            featuredFacts: ["Tonight in New York", "Fast lineup updates", "Clubs worth saving"],
            momentCards: [
                .init(kicker: "Shows tonight", title: "Start with rooms already filling up", detail: "Comedy Cellar, Gotham, The Stand"),
                .init(kicker: "Near you", title: "Keep discovery local first", detail: "Browse nearby comics before opening the full search"),
            ]
        ),
        performers: [
            .init(name: "Nate Jackson", initials: "NJ", note: "Popular sets drawing big room demand this week", primaryColor: Color(hex: "#8F7148") ?? .brown, secondaryColor: Color(hex: "#B49264") ?? .brown),
            .init(name: "Jordan Jensen", initials: "JJ", note: "Fast-rising dates fans are already tracking", primaryColor: Color(hex: "#8E5A34") ?? .brown, secondaryColor: Color(hex: "#D6B290") ?? .brown),
            .init(name: "Josh Johnson", initials: "JJ", note: "Sharp touring momentum across featured clubs", primaryColor: Color(hex: "#403126") ?? .brown, secondaryColor: Color(hex: "#9E7B4B") ?? .brown),
            .init(name: "Zarna Garg", initials: "ZG", note: "Strong crossover interest and packed upcoming runs", primaryColor: Color(hex: "#6F3E26") ?? .orange, secondaryColor: Color(hex: "#C78D59") ?? .orange),
        ],
        nearYouPerformers: [
            .init(name: "Gina Brillon", initials: "GB", note: "Appearing across Manhattan rooms this week", primaryColor: Color(hex: "#553126") ?? .brown, secondaryColor: Color(hex: "#B6845A") ?? .brown),
            .init(name: "Mark Normand", initials: "MN", note: "Nearby dates with strong lineup pull", primaryColor: Color(hex: "#4C3429") ?? .brown, secondaryColor: Color(hex: "#A86C47") ?? .orange),
            .init(name: "Sam Morril", initials: "SM", note: "Easy local add when you want a polished headliner set", primaryColor: Color(hex: "#5C4637") ?? .brown, secondaryColor: Color(hex: "#C39A6B") ?? .brown),
            .init(name: "Rosebud Baker", initials: "RB", note: "Neighborhood shows that keep the feed feeling current", primaryColor: Color(hex: "#3B261C") ?? .brown, secondaryColor: Color(hex: "#8C623F") ?? .orange),
        ],
        tonightShows: [
            .init(venue: "Comedy Cellar", title: "Village Standouts", date: "April 21 at 8:00 PM EDT", location: "117 MacDougal St, New York, NY", lineup: "Mark Normand, Sam Morril", price: "$28"),
            .init(venue: "Gotham Comedy Club", title: "Tonight’s Headliner Mix", date: "April 21 at 8:30 PM EDT", location: "208 W 23rd St, New York, NY", lineup: "Gina Brillon, Jordan Jensen", price: "$25"),
            .init(venue: "The Stand", title: "Late Show Favorites", date: "April 21 at 9:45 PM EDT", location: "116 E 16th St, New York, NY", lineup: "Josh Johnson, Rosebud Baker", price: "$32"),
        ],
        nearbyShows: [
            .init(venue: "Union Hall", title: "Brooklyn Comedy Drop-In", date: "April 23 at 7:30 PM EDT", location: "702 Union St, Brooklyn, NY", lineup: "Gina Brillon, Zarna Garg", price: "$22"),
            .init(venue: "The Bell House", title: "Neighborhood Spotlight", date: "April 24 at 8:00 PM EDT", location: "149 7th St, Brooklyn, NY", lineup: "Josh Johnson, Jordan Jensen", price: "$24"),
            .init(venue: "New York Comedy Club", title: "East Village Late Set", date: "April 25 at 9:30 PM EDT", location: "85 E 4th St, New York, NY", lineup: "Sam Morril, Rosebud Baker", price: "$27"),
        ],
        trendingShows: [
            .init(venue: "The Masonic", title: "Nate Jackson Live", date: "April 24 at 8:00 PM PDT", location: "1111 California St, San Francisco, CA", lineup: "Nate Jackson", price: "$49"),
            .init(venue: "Comedy Cellar", title: "Weekend Showcase", date: "April 25 at 8:00 PM EDT", location: "117 MacDougal St, New York, NY", lineup: "Mark Normand, Jordan Jensen", price: "$25"),
            .init(venue: "The Stand", title: "Crowd Favorites", date: "April 26 at 9:00 PM EDT", location: "116 E 16th St, New York, NY", lineup: "Josh Johnson, Zarna Garg", price: "$34"),
        ],
        clubs: [
            .init(name: "Comedy Cellar", badge: "MacDougal", note: "Legendary lineups and dependable depth make it the anchor room for comedy discovery.", meta: "71 active comedians", primaryColor: Color(hex: "#2E1A14") ?? .black, secondaryColor: Color(hex: "#7A4A2A") ?? .brown),
            .init(name: "The Stand", badge: "Union Square", note: "A polished room with high-energy bills that fit the product’s premium feel.", meta: "48 active comedians", primaryColor: Color(hex: "#2D2421") ?? .black, secondaryColor: Color(hex: "#A6663E") ?? .orange),
            .init(name: "Gotham Comedy Club", badge: "Chelsea", note: "Strong nightly turnover and recognizable talent make it ideal for a native club rail.", meta: "52 active comedians", primaryColor: Color(hex: "#0E0A07") ?? .black, secondaryColor: Color(hex: "#3B2B20") ?? .brown),
        ],
        palette: [
            .init(name: "Canvas", color: Color(hex: "#FAF6E0") ?? .white),
            .init(name: "Cedar", color: Color(hex: "#361E14") ?? .brown),
            .init(name: "Copper", color: Color(hex: "#B87333") ?? .orange),
        ]
    )
}

private struct HomeHeroContent {
    let eyebrow: String
    let title: String
    let subtitle: String
    let pills: [String]
    let featuredFacts: [String]
    let momentCards: [HeroMomentCardContent]
}

private struct HeroMomentCardContent {
    let kicker: String
    let title: String
    let detail: String
}

private struct FeaturedPerformer {
    let name: String
    let initials: String
    let note: String
    let primaryColor: Color
    let secondaryColor: Color
}

private struct FeaturedShow {
    let venue: String
    let title: String
    let date: String
    let location: String
    let lineup: String
    let price: String
}

private struct FeaturedClub {
    let name: String
    let badge: String
    let note: String
    let meta: String
    let primaryColor: Color
    let secondaryColor: Color
}

private struct PaletteItem {
    let name: String
    let color: Color
}

private struct LaughTrackNavigationChrome: ViewModifier {
    let background: Color

    func body(content: Content) -> some View {
        #if os(iOS)
        content
            .toolbarBackground(background, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
        #else
        content
        #endif
    }
}

private struct LaughTrackInlineNavigationTitle: ViewModifier {
    func body(content: Content) -> some View {
        #if os(iOS)
        content.navigationBarTitleDisplayMode(.inline)
        #else
        content
        #endif
    }
}
