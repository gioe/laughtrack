import SwiftUI
import LaughTrackBridge
import LaughTrackCore
#if canImport(UIKit)
import UIKit
#endif

/// Keep mutation outcomes typed until their presentation is selected. Failures
/// must never be mistaken for the routine confirmations that auto-dismiss.
@MainActor
enum DetailActionFeedback: Equatable {
    case toast(String)
    case signIn
    case alert(String)

    static func savedShow(_ result: SavedShowStore.MutationResult) -> Self {
        switch result {
        case .updated(let saved):
            return .toast(saved ? "Saved to your Library." : "Removed from your Library.")
        case .queued(let saved):
            return .toast(saved
                ? "Saved offline. We’ll sync when you’re connected."
                : "Removal saved offline. We’ll sync when you’re connected.")
        case .signInRequired: return .signIn
        case .failure(let message): return .alert(message)
        }
    }

    static func favorite(_ result: ComedianFavoriteStore.ToggleResult, name: String) -> Self {
        switch result {
        case .updated(let next): return .toast(FavoriteFeedback.message(for: name, isFavorite: next))
        case .signInRequired: return .signIn
        case .failure(let message): return .alert(message)
        }
    }

    static func favorite(_ result: ClubFavoriteStore.ToggleResult, name: String) -> Self {
        switch result {
        case .updated(let next): return .toast(FavoriteFeedback.message(for: name, isFavorite: next))
        case .signInRequired: return .signIn
        case .failure(let message): return .alert(message)
        }
    }

    static func favorite(_ result: PodcastFavoriteStore.ToggleResult, name: String) -> Self {
        switch result {
        case .updated(let next): return .toast(FavoriteFeedback.message(for: name, isFavorite: next))
        case .signInRequired: return .signIn
        case .failure(let message): return .alert(message)
        }
    }

    func present(
        using manager: ToastManager,
        signIn: () -> Void,
        alert: (String) -> Void,
        announce: (String) -> Void = DetailActionFeedback.announce
    ) {
        switch self {
        case .toast(let message):
            manager.show(message, type: .info)
            announce(message)
        case .signIn:
            manager.dismiss()
            signIn()
        case .alert(let message):
            manager.dismiss()
            alert(message)
        }
    }

    private static func announce(_ message: String) {
        #if canImport(UIKit)
        // Announce without moving focus away from the save/favorite control.
        UIAccessibility.post(notification: .announcement, argument: message)
        #endif
    }
}

/// The manager owns replacement and auto-dismissal. This renderer belongs to
/// the outer navigation stack, so pushing another detail cannot unmount it.
struct DetailActionToast: View {
    @ObservedObject var manager: ToastManager
    @Environment(\.appTheme) private var theme

    var body: some View {
        if let toast = manager.currentToast {
            HStack(spacing: 12) {
                Image(systemName: toast.type.icon)
                    .foregroundStyle(theme.laughTrackTokens.colors.accentStrong)
                    .accessibilityHidden(true)
                Text(toast.message)
                    .font(.subheadline)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
                Button(action: manager.dismiss) {
                    Image(systemName: "xmark")
                        .frame(width: 44, height: 44)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Dismiss confirmation")
            }
            .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
            .padding(.leading, 16)
            .padding(.trailing, 4)
            .padding(.vertical, 8)
            .background(theme.laughTrackTokens.colors.surfaceMuted,
                        in: RoundedRectangle(cornerRadius: 16))
            .overlay {
                RoundedRectangle(cornerRadius: 16)
                    .stroke(theme.laughTrackTokens.colors.borderStrong, lineWidth: 1)
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 8)
            // Feedback is immediate even when surrounding navigation animates.
            .transaction { $0.animation = nil }
        }
    }
}

struct DetailActionFeedbackOverlay: ViewModifier {
    let manager: ToastManager
    let clearsRootTabBar: Bool
    @Environment(\.appTheme) private var theme

    func body(content: Content) -> some View {
        content.overlay(alignment: .bottom) {
            DetailActionToast(manager: manager)
                .padding(.bottom, PodcastMiniPlayerLayout.bottomPadding(
                    theme: theme, clearsRootTabBar: clearsRootTabBar
                ))
        }
    }
}
