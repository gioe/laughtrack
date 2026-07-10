import Foundation
import SwiftUI
import LaughTrackBridge

/// Entity kind rendered when artwork is missing or fails to load, mirroring the
/// Android RemoteImageFallback enum (TASK-3716) and the icon vocabulary the home
/// rails, search surfaces, and detail heroes already use. Pick the kind matching
/// what the image depicts; `.generic` is the default for surfaces with no single
/// entity.
enum ArtworkFallbackKind {
    case comedian
    case club
    case show
    case podcast
    case person
    case generic

    var systemImage: String {
        switch self {
        case .comedian: return "music.mic"
        case .club: return "building.2.fill"
        case .show: return "ticket.fill"
        case .podcast: return "headphones"
        case .person: return "person.fill"
        case .generic: return "photo"
        }
    }
}

struct RemoteImageView: View {
    @Environment(\.appTheme) private var theme

    let urlString: String
    let aspectRatio: CGFloat
    var alignment: Alignment = .center
    var fallback: ArtworkFallbackKind = .generic

    var body: some View {
        Group {
            if let url = URL.normalizedExternalURL(urlString.trimmingCharacters(in: .whitespacesAndNewlines)) {
                CachedAsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: alignment)
                } placeholder: {
                    placeholderArtwork
                } error: { _ in
                    fallbackArtwork
                }
            } else {
                fallbackArtwork
            }
        }
        .aspectRatio(aspectRatio, contentMode: .fill)
        .clipped()
    }

    private var placeholderArtwork: some View {
        Rectangle()
            .fill(theme.laughTrackTokens.colors.surfaceElevated)
            .overlay {
                ProgressView()
            }
    }

    private var fallbackArtwork: some View {
        let laughTrack = theme.laughTrackTokens
        return Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: fallback.systemImage)
                    .font(.system(size: 44, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }
}

struct InlineNavigationTitle: ViewModifier {
    func body(content: Content) -> some View {
        #if os(iOS)
        content.navigationBarTitleDisplayMode(.inline)
        #else
        content
        #endif
    }
}
