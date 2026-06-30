import SwiftUI
import LaughTrackBridge

enum DetailNavigationChrome {
    enum Entity {
        case club
        case comedian
        case podcast
        case show
    }

    static let extendsHeroBehindTopSafeArea = true

    /// Additional spacing below the status-bar safe-area inset for the
    /// sticky chrome bar. Hiding the system nav bar does NOT collapse the
    /// overlay's top inset — the chrome bar still receives the status-bar
    /// inset and renders at inset + this offset (see DetailStatusBarScrim,
    /// which relies on that inset to escape upward and cover the clock).
    /// Sits intentionally above the marquee hero's content padding so the
    /// back/favorite chrome reads as status-bar-adjacent rather than
    /// crowding the title row.
    static let stickyChromeTopOffset: CGFloat = 16

    /// Opacity/location stops for the top scrim that fades scrolled content
    /// out before it reaches the status bar clock. The scrim spans from the
    /// physical top of the screen to the bottom of the chrome bar: fully
    /// opaque behind the status bar, fading to clear past the chrome buttons
    /// so it reads as the same treatment as the marquee background's edge
    /// fade.
    static let statusBarScrimStops: [(opacity: Double, location: CGFloat)] = [
        (opacity: 1.0, location: 0),
        (opacity: 0.85, location: 0.55),
        (opacity: 0.0, location: 1)
    ]

    static func title(for entity: Entity) -> String {
        switch entity {
        case .club:
            return "Club"
        case .comedian:
            return "Comedian"
        case .podcast:
            return "Podcast"
        case .show:
            return "Show"
        }
    }
}

struct DetailFavoriteState {
    let isFavorite: Bool
    let isPending: Bool
    let action: () async -> Void
}

struct EntityDetailNavigationChrome: ViewModifier {
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>

    let entity: DetailNavigationChrome.Entity
    let title: String?
    let favoriteState: DetailFavoriteState?

    init(
        entity: DetailNavigationChrome.Entity,
        title: String? = nil,
        favoriteState: DetailFavoriteState? = nil
    ) {
        self.entity = entity
        self.title = title
        self.favoriteState = favoriteState
    }

    func body(content: Content) -> some View {
        #if os(iOS)
        content
            .navigationTitle("")
            .navigationBarHidden(true)
        #else
        content
            .navigationTitle(title ?? DetailNavigationChrome.title(for: entity))
        #endif
    }
}

struct DetailAtmosphereScrollContent: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(Color.clear)
            #if os(iOS)
            .scrollContentBackground(.hidden)
            #endif
    }
}

struct DetailAtmosphereRouteBackground: ViewModifier {
    func body(content: Content) -> some View {
        ZStack {
            LaughTrackAtmosphereBackground()
                .ignoresSafeArea()

            content
        }
    }
}

private struct DetailNavigationTitle: View {
    @Environment(\.appTheme) private var theme

    let text: String

    var body: some View {
        if text.isEmpty {
            EmptyView()
        } else {
            Text(text)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                .lineLimit(2)
                .minimumScaleFactor(0.6)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: 240, minHeight: 38)
                .accessibilityAddTraits(.isHeader)
        }
    }
}

/// Sticky chrome bar overlaid at the top of every detail screen. Hosts the
/// back button (always present), the home button (when the stack is deep
/// enough for back and home to differ), and, when supplied, the favorite
/// toggle. Designed to be applied via `.overlay(alignment: .top)` on the
/// outer detail container so the back button remains tappable regardless of
/// scroll position or load phase.
struct DetailChromeBar: View {
    let onBack: () -> Void
    var onHome: (() -> Void)? = nil
    let favoriteState: DetailFavoriteState?

    var body: some View {
        HStack(alignment: .center) {
            DetailBackButton(action: onBack)

            if let onHome {
                DetailHomeButton(action: onHome)
            }

            Spacer()

            if let favoriteState {
                DetailFavoriteToolbarButton(state: favoriteState)
            }
        }
        .padding(.horizontal, 12)
        .padding(.top, DetailNavigationChrome.stickyChromeTopOffset)
        .background(alignment: .top) {
            DetailStatusBarScrim()
        }
    }
}

/// Top fade behind the sticky chrome so scrolled detail content dims out
/// before it reaches the status bar clock. It stays transparent over the
/// detail page's single atmosphere layer to avoid a visible seam between
/// the header controls and the hero content.
struct DetailStatusBarScrim: View {
    var body: some View {
        LinearGradient(
            stops: DetailNavigationChrome.statusBarScrimStops.map {
                .init(color: Color.black.opacity($0.opacity * 0.24), location: $0.location)
            },
            startPoint: .top,
            endPoint: .bottom
        )
        // The chrome bar overlay still receives the status-bar safe-area
        // inset, so the gradient fills the bar's bounds and then escapes
        // the inset to reach the physical top of the screen and cover the
        // clock.
        .ignoresSafeArea(.container, edges: .top)
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}

struct DetailBackButton: View {
    @Environment(\.appTheme) private var theme

    let action: () -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button(action: action) {
            ZStack {
                Circle()
                    .fill(laughTrack.colors.surface.opacity(0.94))
                    .overlay(
                        Circle()
                            .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                    )

                Image(systemName: "chevron.left")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
            }
            .frame(width: 36, height: 36)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Back")
    }
}

/// Escape hatch for deep detail stacks: detail screens cover the tab bar,
/// so without this the only way home is one back-tap per pushed screen.
struct DetailHomeButton: View {
    @Environment(\.appTheme) private var theme

    let action: () -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button(action: action) {
            ZStack {
                Circle()
                    .fill(laughTrack.colors.surface.opacity(0.94))
                    .overlay(
                        Circle()
                            .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                    )

                Image(systemName: "house")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
            }
            .frame(width: 36, height: 36)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Home")
    }
}

extension TypedNavigationCoordinator where Route == AppRoute {
    /// Pop-to-root action for the detail chrome's home button, or nil when
    /// the stack is shallow enough that back already returns to the root —
    /// a home button at depth one would duplicate the back button.
    var detailHomeAction: (() -> Void)? {
        guard routes.count > 1 else { return nil }
        return { [weak self] in self?.popToRoot() }
    }
}

struct DetailFavoriteToolbarButton: View {
    @Environment(\.appTheme) private var theme

    let state: DetailFavoriteState

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button {
            Task { await state.action() }
        } label: {
            ZStack {
                Circle()
                    .fill(laughTrack.colors.surface.opacity(0.94))
                    .overlay(
                        Circle()
                            .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                    )

                if state.isPending {
                    ProgressView()
                        .progressViewStyle(.circular)
                        .tint(laughTrack.colors.accent)
                } else {
                    Image(systemName: state.isFavorite ? "heart.fill" : "heart")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(state.isFavorite ? laughTrack.colors.accentStrong : laughTrack.colors.textPrimary)
                }
            }
            .frame(width: 36, height: 36)
        }
        .buttonStyle(.plain)
        .disabled(state.isPending)
        .accessibilityLabel(state.isFavorite ? "Remove favorite" : "Add favorite")
    }
}
