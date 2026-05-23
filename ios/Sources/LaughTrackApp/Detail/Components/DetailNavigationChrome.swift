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
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>

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
        let resolvedTitle = title ?? DetailNavigationChrome.title(for: entity)
        #if os(iOS)
        content
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarBackButtonHidden(true)
            .toolbarBackground(.hidden, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    DetailBackButton { coordinator.pop() }
                }
                ToolbarItem(placement: .principal) {
                    DetailNavigationTitle(text: resolvedTitle)
                }
                if let favoriteState {
                    ToolbarItem(placement: .topBarTrailing) {
                        DetailFavoriteToolbarButton(state: favoriteState)
                    }
                }
            }
        #else
        content
            .navigationTitle(resolvedTitle)
        #endif
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

private struct DetailFavoriteToolbarButton: View {
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
