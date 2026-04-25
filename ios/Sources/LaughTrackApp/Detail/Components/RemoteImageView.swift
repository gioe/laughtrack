import Foundation
import SwiftUI
import LaughTrackBridge

struct RemoteImageView: View {
    @Environment(\.appTheme) private var theme

    let urlString: String
    let aspectRatio: CGFloat

    var body: some View {
        AsyncImage(url: URL.normalizedExternalURL(urlString)) { phase in
            switch phase {
            case .empty:
                Rectangle()
                    .fill(theme.laughTrackTokens.colors.surfaceElevated)
                    .overlay {
                        ProgressView()
                    }
            case .success(let image):
                image
                    .resizable()
                    .scaledToFill()
            case .failure:
                Rectangle()
                    .fill(theme.laughTrackTokens.colors.surfaceElevated)
                    .overlay {
                        Image(systemName: "photo")
                            .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                    }
            @unknown default:
                Rectangle()
                    .fill(theme.laughTrackTokens.colors.surfaceElevated)
            }
        }
        .aspectRatio(aspectRatio, contentMode: .fill)
        .clipped()
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
