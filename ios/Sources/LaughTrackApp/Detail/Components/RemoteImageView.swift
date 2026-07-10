import Foundation
import SwiftUI
import LaughTrackBridge

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
