import SwiftUI

enum ClubWallHeadshotCaptionVisibility {
    case visible
    case hidden
}

struct ClubWallHeadshotFrame<Content: View>: View {
    let caption: String
    var captionVisibility: ClubWallHeadshotCaptionVisibility = .visible
    var photoWidth: CGFloat = 72
    var photoHeight: CGFloat = 70
    var frameWidth: CGFloat = 96
    var frameHeight: CGFloat = 106
    var captionFontSize: CGFloat = 5.5
    var captionWidth: CGFloat = 76
    var captionHeight: CGFloat = 10
    var rotationDegrees: Double = 0
    @ViewBuilder let content: Content

    @Environment(\.appTheme) private var theme

    var body: some View {
        framedContent
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(.top, matInset)
        .padding(.horizontal, matInset)
        .padding(.bottom, captionBottomMatInset)
        .frame(width: frameWidth, height: frameHeight)
        .background(HeadshotMatColor())
        .overlay(
            RoundedRectangle(cornerRadius: frameWidth > 110 ? 7 : 5, style: .continuous)
                .stroke(Color.black.opacity(0.72), lineWidth: frameWidth > 110 ? 6 : 5)
        )
        .overlay(
            RoundedRectangle(cornerRadius: frameWidth > 110 ? 7 : 5, style: .continuous)
                .stroke(Color.white.opacity(0.18), lineWidth: 1)
                .padding(frameWidth > 110 ? 6 : 5)
        )
        .clipShape(RoundedRectangle(cornerRadius: frameWidth > 110 ? 7 : 5, style: .continuous))
        .rotationEffect(.degrees(rotationDegrees))
        .shadow(color: .black.opacity(0.44), radius: frameWidth > 110 ? 10 : 8, y: frameWidth > 110 ? 6 : 5)
    }

    @ViewBuilder
    private var framedContent: some View {
        if captionVisibility == .visible {
            VStack(spacing: frameWidth > 110 ? 5 : 4) {
                photo
                captionText
            }
        } else {
            photo
        }
    }

    private var photo: some View {
        content
            .frame(width: photoWidth, height: photoHeight)
            .clipShape(Rectangle())
            .overlay(Rectangle().stroke(Color.black.opacity(0.50), lineWidth: 1))
    }

    private var matInset: CGFloat {
        frameWidth > 110 ? 8 : 6
    }

    private var captionBottomMatInset: CGFloat {
        captionVisibility == .visible ? (frameWidth > 110 ? 8 : 6) : matInset
    }

    private var captionText: some View {
        Text(caption.uppercased())
            .font(.system(size: captionFontSize, weight: .semibold, design: .serif))
            .tracking(frameWidth > 110 ? 0.45 : 0.35)
            .foregroundStyle(Color.black.opacity(0.74))
            .lineLimit(1)
            .minimumScaleFactor(0.55)
            .frame(width: captionWidth, height: captionHeight)
            .background(Color.white.opacity(0.30))
            .accessibilityHidden(true)
    }
}

private struct HeadshotMatColor: View {
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        LinearGradient(
            colors: [
                laughTrack.colors.textPrimary.opacity(0.94),
                Color(red: 0.82, green: 0.76, blue: 0.66),
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }
}
