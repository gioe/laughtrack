import SwiftUI
import LaughTrackAPIClient

private struct SkeletonTextLayoutModifier: ViewModifier {
    @Environment(\.redactionReasons) private var reasons

    @ViewBuilder
    func body(content: Content) -> some View {
        if reasons.contains(.placeholder) {
            // SwiftUI's redacted glyphs can wrap differently from actual text.
            // Keep the original text's measurement as the layout authority.
            content.unredacted().hidden()
                .overlay(alignment: .topLeading) { content }
        } else {
            content
        }
    }
}

extension View {
    func preservingSkeletonTextLayout() -> some View {
        modifier(SkeletonTextLayoutModifier())
    }
}

struct ShowsListSkeleton: View {
    @Environment(\.appTheme) private var theme

    var includesHero: Bool = false
    var rowCount: Int = 5
    // Library and pinned lists retain the full date stub.
    var context: ShowRowContext = .standalone

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.md) {
            if includesHero {
                RoundedRectangle(cornerRadius: theme.laughTrackTokens.radius.card)
                    .fill(theme.laughTrackTokens.colors.surfaceSkeleton)
                    .frame(height: 280)
            }
            VStack(alignment: .leading, spacing: theme.spacing.sm) {
                if context == .agenda {
                    Text("Wednesday, September 16")
                        .font(theme.laughTrackTokens.typography.sectionTitle)
                        .fixedSize(horizontal: false, vertical: true)
                }
                AdaptiveSearchResults(spacing: theme.spacing.md) {
                    ForEach(0..<rowCount, id: \.self) { _ in
                        ShowRow(show: Self.placeholder, presentation: .compactTicket, context: context)
                    }
                }
            }
        }
        .redacted(reason: .placeholder)
        .detailSkeletonShimmer()
        .allowsHitTesting(false)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Loading shows")
    }

    // Inert local content supplies typography and wrapping to the real row.
    // Nothing is fetched, navigable, or exposed as an actual search result.
    static let placeholder = Components.Schemas.Show(
        id: 0, clubId: 0, clubName: "Comedy Club", clubCity: "New York", clubState: "NY",
        date: Date(timeIntervalSince1970: 1_789_603_200),
        tickets: [.init(price: 35, purchaseUrl: "", soldOut: false, _type: "General admission")],
        name: "Comedy tonight", room: "Main Room", imageUrl: "", timezone: "America/New_York"
    )
}

struct ComediansListSkeleton: View {
    var body: some View { EntityRowsSkeleton(kind: .comedian, label: "Loading comedians") }
}

struct ClubsListSkeleton: View {
    var body: some View { EntityRowsSkeleton(kind: .club, label: "Loading clubs") }
}

struct PodcastsListSkeleton: View {
    var body: some View { EntityRowsSkeleton(kind: .podcast, label: "Loading podcasts") }
}

struct EntityRowsSkeleton: View {
    @Environment(\.appTheme) private var theme
    let kind: LaughTrackSearchEntityKind
    let label: String

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.md) {
            SearchLoadingSummary()
            AdaptiveSearchResults(spacing: theme.spacing.md) {
                ForEach(0..<5, id: \.self) { _ in
                    row
                }
            }
        }
        .redacted(reason: .placeholder)
        .detailSkeletonShimmer()
        .allowsHitTesting(false)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(label)
    }

    @ViewBuilder
    var row: some View {
        if kind == .club {
            LaughTrackSearchEntityRow(
                title: "Comedy Club", subtitle: "New York, NY", imageURL: nil, kind: kind, action: {}
            )
        } else {
            LaughTrackSearchEntityRow(
                title: kind == .comedian ? "Comedian name" : "Comedy podcast",
                subtitle: kind == .comedian ? nil : "Podcast creator",
                imageURL: nil, kind: kind, action: {}
            ) {
                RoundedRectangle(cornerRadius: 4)
                    .fill(theme.laughTrackTokens.colors.surfaceSkeleton)
                    .frame(width: 20, height: 20)
                    .frame(width: 44, height: 44)
            }
        }
    }
}

/// Reserves the same scaled status height as SearchResultsSummary without
/// presenting an invented result count to VoiceOver.
struct SearchLoadingSummary: View {
    @Environment(\.appTheme) private var theme
    @ScaledMetric(relativeTo: .caption) private var statusHeight = 44

    var body: some View {
        HStack {
            Text("Showing results")
                .font(theme.laughTrackTokens.typography.metadata)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: theme.spacing.sm)
        }
        .frame(minHeight: statusHeight)
        .redacted(reason: .placeholder)
        .accessibilityHidden(true)
    }
}
