import SwiftUI
import LaughTrackBridge
#if canImport(UIKit)
import UIKit
import AVKit
#endif

struct NowPlayingView: View {
    @ObservedObject var player: PodcastPlaybackController
    @Environment(\.dismiss) private var dismiss
    @Environment(\.appTheme) private var theme

    @State private var isScrubbing = false
    @State private var scrubValue: Double = 0

    private static let sleepIntervals: [(label: String, seconds: TimeInterval?)] = [
        ("Off", nil),
        ("5 min", 5 * 60),
        ("10 min", 10 * 60),
        ("15 min", 15 * 60),
        ("30 min", 30 * 60),
        ("45 min", 45 * 60),
        ("1 hour", 60 * 60)
    ]

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack(alignment: .top) {
            laughTrack.colors.canvas.ignoresSafeArea()

            VStack(spacing: theme.spacing.lg) {
                grabber
                header
                artwork
                titleBlock
                scrubber
                transport
                routeAndSpeed
                sleepTimer
                Spacer(minLength: 0)
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.top, theme.spacing.sm)
            .padding(.bottom, theme.spacing.lg)
        }
        .presentationDragIndicator(.hidden)
        .accessibilityIdentifier("laughtrack.now-playing-screen")
    }

    private var grabber: some View {
        let laughTrack = theme.laughTrackTokens
        return Capsule()
            .fill(laughTrack.colors.borderStrong.opacity(0.45))
            .frame(width: 44, height: 5)
            .padding(.top, theme.spacing.xs)
    }

    private var header: some View {
        let laughTrack = theme.laughTrackTokens
        return HStack(spacing: theme.spacing.sm) {
            Button {
                dismiss()
            } label: {
                Image(systemName: "chevron.down")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .frame(width: 36, height: 36)
                    .background(laughTrack.colors.surfaceElevated)
                    .clipShape(Circle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Close now playing")

            Spacer(minLength: 0)

            Text("Now Playing")
                .font(laughTrack.typography.metadata.weight(.semibold))
                .foregroundStyle(laughTrack.colors.textSecondary)

            Spacer(minLength: 0)

            Color.clear
                .frame(width: 36, height: 36)
        }
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens
        let imageURLString = player.currentItem?.podcastImageURL?.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolved = (imageURLString?.isEmpty ?? true) ? nil : imageURLString
        let spotlightColor = player.accentColorOverride ?? laughTrack.colors.accent

        ZStack {
            PodcastSpotlightView(isActive: player.isPlaying, color: spotlightColor)
                .padding(-32)

            artworkImage(resolved: resolved)
                .frame(maxWidth: .infinity)
                .aspectRatio(1, contentMode: .fit)
                .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
                .shadowStyle(laughTrack.shadows.floating)
        }
        .padding(.horizontal, theme.spacing.md)
    }

    @ViewBuilder
    private func artworkImage(resolved: String?) -> some View {
        if let raw = resolved, let url = URL.normalizedExternalURL(raw) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                artworkFallback
            } error: { _ in
                artworkFallback
            }
        } else {
            artworkFallback
        }
    }

    private var artworkFallback: some View {
        let laughTrack = theme.laughTrackTokens
        return RoundedRectangle(cornerRadius: 24, style: .continuous)
            .fill(laughTrack.colors.surfaceElevated)
            .overlay {
                Image(systemName: "music.mic")
                    .font(.system(size: 72, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

    @ViewBuilder
    private var titleBlock: some View {
        let laughTrack = theme.laughTrackTokens
        VStack(spacing: 6) {
            Text(player.currentItem?.episodeTitle ?? "")
                .font(.system(.title2, design: .serif, weight: .heavy))
                .foregroundStyle(laughTrack.colors.textPrimary)
                .multilineTextAlignment(.center)
                .lineLimit(3)

            Text(player.currentItem?.podcastName ?? "")
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .multilineTextAlignment(.center)
                .lineLimit(2)
        }
    }

    @ViewBuilder
    private var scrubber: some View {
        let laughTrack = theme.laughTrackTokens
        let duration = max(player.duration, 0)
        let displayValue = isScrubbing ? scrubValue : player.currentTime
        let remaining = max(0, duration - displayValue)

        VStack(spacing: 6) {
            Slider(
                value: Binding(
                    get: { displayValue },
                    set: { newValue in
                        scrubValue = newValue
                    }
                ),
                in: 0...max(duration, 0.001),
                onEditingChanged: { editing in
                    if editing {
                        isScrubbing = true
                        scrubValue = displayValue
                    } else {
                        isScrubbing = false
                        player.seek(to: scrubValue)
                    }
                }
            )
            .tint(laughTrack.colors.accent)
            .disabled(duration <= 0)

            HStack {
                Text(formatTime(displayValue))
                    .font(laughTrack.typography.metadata.monospacedDigit())
                    .foregroundStyle(laughTrack.colors.textSecondary)
                Spacer()
                Text("-" + formatTime(remaining))
                    .font(laughTrack.typography.metadata.monospacedDigit())
                    .foregroundStyle(laughTrack.colors.textSecondary)
            }
        }
    }

    @ViewBuilder
    private var transport: some View {
        let laughTrack = theme.laughTrackTokens
        HStack(spacing: theme.spacing.xl) {
            Button {
                player.skipBack()
            } label: {
                Image(systemName: "gobackward.15")
                    .font(.system(size: 36, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Skip back 15 seconds")

            Button {
                player.togglePlayPause()
            } label: {
                Image(systemName: player.isPlaying ? "pause.fill" : "play.fill")
                    .font(.system(size: 32, weight: .bold))
                    .foregroundStyle(laughTrack.colors.textInverse)
                    .frame(width: 76, height: 76)
                    .background(laughTrack.colors.accent)
                    .clipShape(Circle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(player.isPlaying ? "Pause" : "Play")

            Button {
                player.skipForward()
            } label: {
                Image(systemName: "goforward.30")
                    .font(.system(size: 36, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Skip forward 30 seconds")
        }
    }

    @ViewBuilder
    private var routeAndSpeed: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.lg) {
            Menu {
                ForEach(PodcastPlaybackController.supportedRates, id: \.self) { rate in
                    Button {
                        player.setRate(rate)
                    } label: {
                        if abs(player.preferredRate - rate) < 0.01 {
                            Label(formatRate(rate), systemImage: "checkmark")
                        } else {
                            Text(formatRate(rate))
                        }
                    }
                }
            } label: {
                Text(formatRate(player.preferredRate))
                    .font(laughTrack.typography.body.weight(.semibold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 8)
                    .background(laughTrack.colors.surfaceElevated)
                    .clipShape(Capsule())
            }
            .accessibilityLabel("Playback speed \(formatRate(player.preferredRate))")

            Spacer(minLength: 0)

            routePicker
                .frame(width: 44, height: 44)
        }
        .padding(.horizontal, theme.spacing.sm)
    }

    @ViewBuilder
    private var routePicker: some View {
        #if canImport(UIKit) && !targetEnvironment(macCatalyst)
        AirPlayRoutePicker(tint: theme.laughTrackTokens.colors.accent)
            .accessibilityLabel("AirPlay")
        #else
        Image(systemName: "airplayaudio")
            .font(.system(size: 22, weight: .semibold))
            .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
        #endif
    }

    @ViewBuilder
    private var sleepTimer: some View {
        let laughTrack = theme.laughTrackTokens

        Menu {
            ForEach(Array(Self.sleepIntervals.enumerated()), id: \.offset) { _, choice in
                Button {
                    player.setSleepTimer(choice.seconds)
                } label: {
                    if isCurrentSleep(choice.seconds) {
                        Label(choice.label, systemImage: "checkmark")
                    } else {
                        Text(choice.label)
                    }
                }
            }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "moon.zzz.fill")
                    .font(.system(size: 16, weight: .semibold))
                Text(sleepLabel)
                    .font(laughTrack.typography.metadata.weight(.semibold))
            }
            .foregroundStyle(laughTrack.colors.textPrimary)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(laughTrack.colors.surfaceElevated)
            .clipShape(Capsule())
        }
        .accessibilityLabel("Sleep timer \(sleepLabel)")
    }

    private var sleepLabel: String {
        guard let endsAt = player.sleepTimerEndsAt else { return "Sleep" }
        let remaining = max(0, endsAt.timeIntervalSinceNow)
        return "Sleep · " + formatTime(remaining)
    }

    private func isCurrentSleep(_ seconds: TimeInterval?) -> Bool {
        switch (seconds, player.sleepTimerInterval) {
        case (nil, nil):
            return true
        case (.some(let chosen), .some(let active)):
            return abs(chosen - active) < 0.5
        default:
            return false
        }
    }

    private func formatTime(_ seconds: TimeInterval) -> String {
        guard seconds.isFinite, seconds >= 0 else { return "0:00" }
        let total = Int(seconds.rounded())
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let secs = total % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, secs)
        }
        return String(format: "%d:%02d", minutes, secs)
    }

    private func formatRate(_ rate: Float) -> String {
        if rate.truncatingRemainder(dividingBy: 1) == 0 {
            return String(format: "%.0fx", rate)
        }
        let formatted = String(format: "%.2f", rate)
        let trimmed = formatted
            .replacingOccurrences(of: "0+$", with: "", options: .regularExpression)
            .replacingOccurrences(of: "\\.$", with: "", options: .regularExpression)
        return "\(trimmed)x"
    }
}

#if canImport(UIKit) && !targetEnvironment(macCatalyst)
private struct AirPlayRoutePicker: UIViewRepresentable {
    let tint: Color

    func makeUIView(context: Context) -> AVRoutePickerView {
        let view = AVRoutePickerView()
        view.activeTintColor = UIColor(tint)
        view.tintColor = UIColor(tint)
        view.prioritizesVideoDevices = false
        view.backgroundColor = .clear
        return view
    }

    func updateUIView(_ uiView: AVRoutePickerView, context: Context) {
        uiView.activeTintColor = UIColor(tint)
        uiView.tintColor = UIColor(tint)
    }
}
#endif
