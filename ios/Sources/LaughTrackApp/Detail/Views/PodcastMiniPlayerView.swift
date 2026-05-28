import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge

struct PodcastMiniPlayerView: View {
    @ObservedObject var player: PodcastPlaybackController
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL
    @State private var isExpanded = false
    @State private var dragOffset: CGFloat = 0

    private static let dismissThreshold: CGFloat = 60

    var body: some View {
        if let item = player.currentItem {
            content(item: item)
                .offset(y: dragOffset)
                .gesture(dismissGesture)
                .sheet(isPresented: $isExpanded) {
                    NowPlayingView(player: player, apiClient: apiClient)
                        .presentationDetents([.large])
                }
        }
    }

    @ViewBuilder
    private func content(item: PodcastPlaybackItem) -> some View {
        let laughTrack = theme.laughTrackTokens

        Button(action: expand) {
            VStack(spacing: 0) {
                HStack(spacing: 12) {
                    artwork(item: item)
                        .frame(width: 44, height: 44)
                        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))

                    VStack(alignment: .leading, spacing: 2) {
                        Text(item.episodeTitle)
                            .font(laughTrack.typography.body.weight(.semibold))
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .lineLimit(1)

                        Text(item.podcastName)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .lineLimit(1)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    transportCluster(item: item)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)

                progressBar
            }
        }
        .buttonStyle(.plain)
        .frame(maxWidth: .infinity)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.floating)
        .accessibilityIdentifier(LaughTrackViewTestID.podcastMiniPlayer)
    }

    @ViewBuilder
    private func transportCluster(item: PodcastPlaybackItem) -> some View {
        let laughTrack = theme.laughTrackTokens

        if item.requiresExternalFallback {
            if let episodeURL = item.episodeURL {
                Button {
                    openURL(episodeURL)
                } label: {
                    Image(systemName: "arrow.up.right.square")
                        .font(.system(size: theme.iconSizes.md, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .frame(width: 38, height: 38)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Open episode")
            }
        } else {
            HStack(spacing: 6) {
                Button {
                    player.skipBack()
                } label: {
                    Image(systemName: "gobackward.15")
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .frame(width: 36, height: 36)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Skip back 15 seconds")

                Button {
                    player.togglePlayPause()
                } label: {
                    Image(systemName: player.isPlaying ? "pause.fill" : "play.fill")
                        .font(.system(size: theme.iconSizes.md, weight: .bold))
                        .foregroundStyle(laughTrack.colors.textInverse)
                        .frame(width: 38, height: 38)
                        .background(laughTrack.colors.accentStrong)
                        .clipShape(Circle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(player.isPlaying ? "Pause podcast" : "Play podcast")

                Button {
                    player.skipForward()
                } label: {
                    Image(systemName: "goforward.30")
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .frame(width: 36, height: 36)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Skip forward 30 seconds")
            }
        }
    }

    @ViewBuilder
    private func artwork(item: PodcastPlaybackItem) -> some View {
        let laughTrack = theme.laughTrackTokens
        let raw = item.podcastImageURL?.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolved = (raw?.isEmpty ?? true) ? nil : raw

        if let raw = resolved, let url = URL.normalizedExternalURL(raw) {
            CachedAsyncImage(url: url) { image in
                image.resizable().scaledToFill()
            } placeholder: {
                fallbackArtwork
            } error: { _ in
                fallbackArtwork
            }
        } else if item.requiresExternalFallback {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(laughTrack.colors.surfaceMuted)
                .overlay {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.warning)
                }
        } else {
            fallbackArtwork
        }
    }

    private var fallbackArtwork: some View {
        let laughTrack = theme.laughTrackTokens
        return RoundedRectangle(cornerRadius: 8, style: .continuous)
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "music.mic")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

    @ViewBuilder
    private var progressBar: some View {
        let laughTrack = theme.laughTrackTokens
        let duration = player.duration
        let fraction = duration > 0 ? min(1, max(0, player.currentTime / duration)) : 0

        GeometryReader { proxy in
            ZStack(alignment: .leading) {
                Rectangle()
                    .fill(laughTrack.colors.borderSubtle.opacity(0.5))
                Rectangle()
                    .fill(laughTrack.colors.accent)
                    .frame(width: proxy.size.width * fraction)
            }
        }
        .frame(height: 2)
    }

    private var dismissGesture: some Gesture {
        DragGesture()
            .onChanged { value in
                guard value.translation.height > 0 else { return }
                dragOffset = value.translation.height
            }
            .onEnded { value in
                if value.translation.height > Self.dismissThreshold {
                    withAnimation(.easeIn(duration: 0.18)) {
                        dragOffset = 240
                    }
                    Task { @MainActor in
                        try? await Task.sleep(nanoseconds: 180_000_000)
                        dragOffset = 0
                        player.dismiss()
                    }
                } else {
                    withAnimation(.spring(response: 0.32, dampingFraction: 0.85)) {
                        dragOffset = 0
                    }
                }
            }
    }

    private func expand() {
        isExpanded = true
    }
}
