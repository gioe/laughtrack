import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
#if canImport(UIKit)
import UIKit
#endif

struct PodcastMiniPlayerView: View {
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @ObservedObject var player: PodcastPlaybackController
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isExpanded = false
    @GestureState(resetTransaction: Transaction(animation: .easeOut(duration: 0.18)))
    private var dragOffset: CGFloat = 0

    private static let dismissThreshold: CGFloat = 60

    #if canImport(UIKit)
    private var presentsNowPlayingFullScreen: Bool {
        if UIDevice.current.userInterfaceIdiom == .pad {
            return true
        }

        #if DEBUG
        return ProcessInfo.processInfo.environment[UITestLaunchArgs.forceComparisonScreens] == "1"
        #else
        return false
        #endif
    }
    #endif

    var body: some View {
        if let item = player.currentItem {
            presentedContent(item: item)
        }
    }

    @ViewBuilder
    private func presentedContent(item: PodcastPlaybackItem) -> some View {
        let miniPlayer = content(item: item)
            .offset(y: dragOffset)
            .highPriorityGesture(dismissGesture)
            .transaction { transaction in
                if reduceMotion { transaction.animation = nil }
            }
            .accessibilityAction(named: Text("Dismiss player")) {
                player.dismiss()
            }

        #if canImport(UIKit)
        if presentsNowPlayingFullScreen {
            miniPlayer
                .fullScreenCover(isPresented: $isExpanded) {
                    NowPlayingView(player: player, apiClient: apiClient)
                }
        } else {
            miniPlayer
                .sheet(isPresented: $isExpanded) {
                    NowPlayingView(player: player, apiClient: apiClient)
                        .presentationDetents([.large])
                }
        }
        #else
        miniPlayer
            .sheet(isPresented: $isExpanded) {
                NowPlayingView(player: player, apiClient: apiClient)
                    .presentationDetents([.large])
            }
        #endif
    }

    @ViewBuilder
    private func content(item: PodcastPlaybackItem) -> some View {
        let laughTrack = theme.laughTrackTokens

        VStack(spacing: 0) {
            (dynamicTypeSize.isAccessibilitySize
                ? AnyLayout(VStackLayout(alignment: .leading, spacing: 8))
                : AnyLayout(HStackLayout(spacing: 12))) {
                Button(action: expand) {
                    HStack(spacing: 12) {
                        artwork(item: item)
                            .frame(width: 44, height: 44)
                            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                            .accessibilityHidden(true)

                        VStack(alignment: .leading, spacing: 2) {
                            Text(item.episodeTitle)
                                .font(laughTrack.typography.body.weight(.semibold))
                                .foregroundStyle(laughTrack.colors.textPrimary)
                                .lineLimit(dynamicTypeSize.isAccessibilitySize ? 2 : 1)
                            Text(item.podcastName)
                                .font(laughTrack.typography.metadata)
                                .foregroundStyle(laughTrack.colors.textSecondary)
                                .lineLimit(1)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .frame(minHeight: 44)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Open player for \(item.episodeTitle), \(item.podcastName)")

                transportCluster(item: item)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)

            progressBar
                .accessibilityHidden(true)
        }
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
                        .frame(width: 44, height: 44)
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
                        .frame(width: 44, height: 44)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Skip back 15 seconds")

                Button {
                    player.togglePlayPause()
                } label: {
                    Image(systemName: player.isPlaying ? "pause.fill" : "play.fill")
                        .font(.system(size: theme.iconSizes.md, weight: .bold))
                        .foregroundStyle(laughTrack.colors.textInverse)
                        .frame(width: 44, height: 44)
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
                        .frame(width: 44, height: 44)
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
                Image(systemName: ArtworkFallbackKind.podcast.systemImage)
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
            .updating($dragOffset) { value, offset, _ in
                offset = max(0, value.translation.height)
            }
            .onEnded { value in
                guard value.translation.height > Self.dismissThreshold else { return }
                // Commit to the current interaction immediately. A delayed task
                // could otherwise dismiss a replacement episode after navigation.
                withAnimation(reduceMotion ? nil : .easeOut(duration: 0.18)) {
                    player.dismiss()
                }
            }
    }

    private func expand() {
        isExpanded = true
    }
}
