import SwiftUI
import AVFoundation
import Combine
import MediaPlayer
#if canImport(UIKit)
import UIKit
#endif

@MainActor
protocol PodcastAudioEngine: AnyObject {
    func load(url: URL, onFailure: @escaping () -> Void)
    func play()
    func pause()
    func stop()

    func seek(to seconds: TimeInterval)
    func setRate(_ rate: Float)
    func setVolume(_ volume: Float)

    var currentTime: TimeInterval { get }
    var duration: TimeInterval { get }
    var rate: Float { get }
    var isBuffering: Bool { get }

    func setObserver(_ handler: @escaping () -> Void)
}

extension PodcastAudioEngine {
    func seek(to seconds: TimeInterval) {}
    func setRate(_ rate: Float) {}
    func setVolume(_ volume: Float) {}
    var currentTime: TimeInterval { 0 }
    var duration: TimeInterval { 0 }
    var rate: Float { 1 }
    var isBuffering: Bool { false }
    func setObserver(_ handler: @escaping () -> Void) {}
}

final class AVPodcastAudioEngine: PodcastAudioEngine {
    private var player: AVPlayer?
    private var statusObservation: NSKeyValueObservation?
    private var rateObservation: NSKeyValueObservation?
    private var bufferingObservation: NSKeyValueObservation?
    private var timeObserverToken: Any?
    private var stateObserver: (() -> Void)?

    var currentTime: TimeInterval {
        guard let player else { return 0 }
        let seconds = player.currentTime().seconds
        return seconds.isFinite ? seconds : 0
    }

    var duration: TimeInterval {
        guard let item = player?.currentItem else { return 0 }
        let seconds = item.duration.seconds
        return seconds.isFinite ? seconds : 0
    }

    var rate: Float { player?.rate ?? 0 }
    private(set) var isBuffering: Bool = false

    func load(url: URL, onFailure: @escaping () -> Void) {
        invalidateObservations()

        let item = AVPlayerItem(url: url)
        statusObservation = item.observe(\.status, options: [.new]) { [weak self] observed, _ in
            let status = observed.status
            Task { @MainActor in
                switch status {
                case .failed:
                    onFailure()
                case .readyToPlay:
                    self?.notifyState()
                default:
                    break
                }
            }
        }

        bufferingObservation = item.observe(\.isPlaybackLikelyToKeepUp, options: [.new]) { [weak self] observed, _ in
            let keepingUp = observed.isPlaybackLikelyToKeepUp
            Task { @MainActor in
                self?.isBuffering = !keepingUp
                self?.notifyState()
            }
        }

        let newPlayer = AVPlayer(playerItem: item)
        rateObservation = newPlayer.observe(\.rate, options: [.new]) { [weak self] _, _ in
            Task { @MainActor in self?.notifyState() }
        }

        timeObserverToken = newPlayer.addPeriodicTimeObserver(
            forInterval: CMTime(seconds: 0.5, preferredTimescale: 600),
            queue: .main
        ) { [weak self] _ in
            MainActor.assumeIsolated { self?.notifyState() }
        }

        player = newPlayer
    }

    func play() {
        configureAudioSession()
        player?.play()
    }

    func pause() {
        player?.pause()
    }

    func stop() {
        invalidateObservations()
        player?.pause()
        player = nil
        isBuffering = false
        deactivateAudioSession()
        notifyState()
    }

    func seek(to seconds: TimeInterval) {
        guard let player else { return }
        let bounded = max(0, seconds)
        let target = CMTime(seconds: bounded, preferredTimescale: 600)
        player.seek(to: target, toleranceBefore: .zero, toleranceAfter: .zero) { [weak self] _ in
            Task { @MainActor in self?.notifyState() }
        }
    }

    func setRate(_ rate: Float) {
        player?.rate = rate
    }

    func setVolume(_ volume: Float) {
        player?.volume = max(0, min(1, volume))
    }

    func setObserver(_ handler: @escaping () -> Void) {
        stateObserver = handler
    }

    private func notifyState() {
        stateObserver?()
    }

    private func invalidateObservations() {
        statusObservation?.invalidate()
        statusObservation = nil
        rateObservation?.invalidate()
        rateObservation = nil
        bufferingObservation?.invalidate()
        bufferingObservation = nil
        if let token = timeObserverToken {
            player?.removeTimeObserver(token)
        }
        timeObserverToken = nil
    }

    private func configureAudioSession() {
        #if canImport(UIKit) && !targetEnvironment(macCatalyst)
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .spokenAudio, options: [])
        try? session.setActive(true, options: [])
        #endif
    }

    private func deactivateAudioSession() {
        #if canImport(UIKit) && !targetEnvironment(macCatalyst)
        try? AVAudioSession.sharedInstance().setActive(false, options: [.notifyOthersOnDeactivation])
        #endif
    }
}

@MainActor
final class PodcastPlaybackController: ObservableObject {
    @Published private(set) var currentItem: PodcastPlaybackItem?
    @Published private(set) var isPlaying = false
    @Published private(set) var currentTime: TimeInterval = 0
    @Published private(set) var duration: TimeInterval = 0
    @Published private(set) var isBuffering = false
    @Published var preferredRate: Float = 1.0 {
        didSet { applyRateIfPlaying() }
    }
    @Published private(set) var sleepTimerEndsAt: Date?
    @Published private(set) var sleepTimerInterval: TimeInterval?
    @Published private(set) var accentColorOverride: Color?

    static let supportedRates: [Float] = [0.8, 1.0, 1.25, 1.5, 1.75, 2.0]
    static let skipBackInterval: TimeInterval = 15
    static let skipForwardInterval: TimeInterval = 30
    static let sleepTimerFadeWindow: TimeInterval = 10
    private static let sleepTimerFadeStepCount = 20

    private let audioEngine: PodcastAudioEngine
    private let registersRemoteCommands: Bool
    private var nowPlayingArtwork: MPMediaItemArtwork?
    private var artworkLoadToken: UUID?
    private var sleepTimer: Task<Void, Never>?
    private var remoteCommandsRegistered = false

    init(
        audioEngine: PodcastAudioEngine? = nil,
        registersRemoteCommands: Bool? = nil
    ) {
        let engine = audioEngine ?? AVPodcastAudioEngine()
        self.audioEngine = engine
        self.registersRemoteCommands = registersRemoteCommands ?? !Self.isRunningTests
        engine.setObserver { [weak self] in
            self?.syncFromEngine()
        }
    }

    // MARK: - Transport

    func start(_ item: PodcastPlaybackItem) {
        let isReplay = currentItem?.id == item.id
        currentItem = item
        guard let audioURL = item.audioURL else {
            audioEngine.stop()
            isPlaying = false
            currentTime = 0
            duration = 0
            clearNowPlayingInfo()
            return
        }

        if !isReplay {
            audioEngine.load(url: audioURL) { [weak self] in
                self?.markCurrentItemFailed()
            }
            nowPlayingArtwork = nil
            currentTime = 0
            duration = 0
            loadArtworkIfNeeded(for: item)
        }
        audioEngine.play()
        audioEngine.setRate(preferredRate)
        isPlaying = true
        registerRemoteCommandsIfNeeded()
        updateNowPlayingInfo()
    }

    func pause() {
        audioEngine.pause()
        isPlaying = false
        updateNowPlayingInfo()
    }

    func resume() {
        guard let item = currentItem, item.audioURL != nil else { return }
        audioEngine.play()
        audioEngine.setRate(preferredRate)
        isPlaying = true
        registerRemoteCommandsIfNeeded()
        updateNowPlayingInfo()
    }

    func togglePlayPause() {
        isPlaying ? pause() : resume()
    }

    func dismiss() {
        audioEngine.stop()
        currentItem = nil
        isPlaying = false
        currentTime = 0
        duration = 0
        accentColorOverride = nil
        cancelSleepTimer()
        clearNowPlayingInfo()
    }

    func seek(to seconds: TimeInterval) {
        guard currentItem?.audioURL != nil else { return }
        let upperBound = duration > 0 ? duration : seconds
        let target = max(0, min(seconds, upperBound))
        audioEngine.seek(to: target)
        currentTime = target
        updateNowPlayingInfo()
    }

    func skipBack() {
        seek(to: currentTime - Self.skipBackInterval)
    }

    func skipForward() {
        seek(to: currentTime + Self.skipForwardInterval)
    }

    func setRate(_ rate: Float) {
        preferredRate = rate
    }

    func markCurrentItemFailed() {
        guard let currentItem else { return }
        audioEngine.stop()
        self.currentItem = currentItem.markingAudioFailed()
        isPlaying = false
        currentTime = 0
        duration = 0
        accentColorOverride = nil
        cancelSleepTimer()
        clearNowPlayingInfo()
    }

    // MARK: - Sleep timer

    func setSleepTimer(_ interval: TimeInterval?) {
        cancelSleepTimer()
        guard let interval, interval > 0 else { return }
        let endsAt = Date().addingTimeInterval(interval)
        sleepTimerEndsAt = endsAt
        sleepTimerInterval = interval
        sleepTimer = Task { [weak self] in
            let fadeDuration = min(interval, Self.sleepTimerFadeWindow)
            let preFadeDelay = max(0, interval - fadeDuration)
            if preFadeDelay > 0 {
                try? await Task.sleep(nanoseconds: UInt64(preFadeDelay * 1_000_000_000))
            }
            await self?.fadeOutAndStopForSleep(durationSeconds: fadeDuration)
        }
    }

    private func fadeOutAndStopForSleep(durationSeconds: TimeInterval) async {
        guard !Task.isCancelled, sleepTimerEndsAt != nil else { return }
        let steps = Self.sleepTimerFadeStepCount
        let stepDuration = durationSeconds / Double(steps)
        for step in (0..<steps).reversed() {
            if Task.isCancelled || sleepTimerEndsAt == nil { return }
            let level = Float(step) / Float(steps)
            audioEngine.setVolume(level)
            if stepDuration > 0 {
                try? await Task.sleep(nanoseconds: UInt64(stepDuration * 1_000_000_000))
            }
        }
        guard !Task.isCancelled, sleepTimerEndsAt != nil else { return }
        sleepTimerEndsAt = nil
        sleepTimerInterval = nil
        pause()
        audioEngine.setVolume(1)
    }

    private func cancelSleepTimer() {
        sleepTimer?.cancel()
        sleepTimer = nil
        sleepTimerEndsAt = nil
        sleepTimerInterval = nil
        audioEngine.setVolume(1)
    }

    // MARK: - Engine bridge

    private func syncFromEngine() {
        let engineCurrent = audioEngine.currentTime
        let engineDuration = audioEngine.duration
        if engineCurrent.isFinite, engineCurrent >= 0 {
            currentTime = engineCurrent
        }
        if engineDuration.isFinite, engineDuration > 0 {
            duration = engineDuration
        }
        isBuffering = audioEngine.isBuffering

        let engineIsPlaying = audioEngine.rate > 0
        if currentItem?.audioURL != nil, engineIsPlaying != isPlaying {
            isPlaying = engineIsPlaying
        }
        updateNowPlayingInfo()
    }

    private func applyRateIfPlaying() {
        guard isPlaying else { return }
        audioEngine.setRate(preferredRate)
        updateNowPlayingInfo()
    }

    // MARK: - Now Playing / Remote Commands

    private func registerRemoteCommandsIfNeeded() {
        guard registersRemoteCommands, !remoteCommandsRegistered else { return }
        remoteCommandsRegistered = true

        let center = MPRemoteCommandCenter.shared()

        center.playCommand.isEnabled = true
        center.playCommand.addTarget { [weak self] _ in
            guard let self else { return .commandFailed }
            return MainActor.assumeIsolated {
                self.resume()
                return .success
            }
        }

        center.pauseCommand.isEnabled = true
        center.pauseCommand.addTarget { [weak self] _ in
            guard let self else { return .commandFailed }
            return MainActor.assumeIsolated {
                self.pause()
                return .success
            }
        }

        center.togglePlayPauseCommand.isEnabled = true
        center.togglePlayPauseCommand.addTarget { [weak self] _ in
            guard let self else { return .commandFailed }
            return MainActor.assumeIsolated {
                self.togglePlayPause()
                return .success
            }
        }

        center.skipBackwardCommand.isEnabled = true
        center.skipBackwardCommand.preferredIntervals = [NSNumber(value: Self.skipBackInterval)]
        center.skipBackwardCommand.addTarget { [weak self] _ in
            guard let self else { return .commandFailed }
            return MainActor.assumeIsolated {
                self.skipBack()
                return .success
            }
        }

        center.skipForwardCommand.isEnabled = true
        center.skipForwardCommand.preferredIntervals = [NSNumber(value: Self.skipForwardInterval)]
        center.skipForwardCommand.addTarget { [weak self] _ in
            guard let self else { return .commandFailed }
            return MainActor.assumeIsolated {
                self.skipForward()
                return .success
            }
        }

        center.changePlaybackPositionCommand.isEnabled = true
        center.changePlaybackPositionCommand.addTarget { [weak self] event in
            guard
                let self,
                let positionEvent = event as? MPChangePlaybackPositionCommandEvent
            else { return .commandFailed }
            return MainActor.assumeIsolated {
                self.seek(to: positionEvent.positionTime)
                return .success
            }
        }

        center.changePlaybackRateCommand.isEnabled = true
        center.changePlaybackRateCommand.supportedPlaybackRates = Self.supportedRates.map { NSNumber(value: $0) }
        center.changePlaybackRateCommand.addTarget { [weak self] event in
            guard
                let self,
                let rateEvent = event as? MPChangePlaybackRateCommandEvent
            else { return .commandFailed }
            return MainActor.assumeIsolated {
                self.setRate(rateEvent.playbackRate)
                return .success
            }
        }
    }

    private func updateNowPlayingInfo() {
        guard registersRemoteCommands else { return }
        guard let item = currentItem, item.audioURL != nil else {
            clearNowPlayingInfo()
            return
        }

        var info: [String: Any] = [
            MPMediaItemPropertyTitle: item.episodeTitle,
            MPMediaItemPropertyAlbumTitle: item.podcastName,
            MPNowPlayingInfoPropertyMediaType: NSNumber(value: MPNowPlayingInfoMediaType.audio.rawValue),
            MPMediaItemPropertyPlaybackDuration: NSNumber(value: duration),
            MPNowPlayingInfoPropertyElapsedPlaybackTime: NSNumber(value: currentTime),
            MPNowPlayingInfoPropertyPlaybackRate: NSNumber(value: isPlaying ? preferredRate : 0),
            MPNowPlayingInfoPropertyDefaultPlaybackRate: NSNumber(value: preferredRate)
        ]
        if let nowPlayingArtwork {
            info[MPMediaItemPropertyArtwork] = nowPlayingArtwork
        }
        MPNowPlayingInfoCenter.default().nowPlayingInfo = info
    }

    private func clearNowPlayingInfo() {
        guard registersRemoteCommands else { return }
        MPNowPlayingInfoCenter.default().nowPlayingInfo = nil
    }

    private func loadArtworkIfNeeded(for item: PodcastPlaybackItem) {
        artworkLoadToken = nil
        nowPlayingArtwork = nil
        accentColorOverride = nil
        guard
            let raw = item.podcastImageURL?.trimmingCharacters(in: .whitespacesAndNewlines),
            !raw.isEmpty,
            let url = URL.normalizedExternalURL(raw)
        else { return }

        let token = UUID()
        artworkLoadToken = token
        Task { [weak self] in
            guard let data = try? await URLSession.shared.data(from: url).0 else { return }
            #if canImport(UIKit)
            guard let image = UIImage(data: data) else { return }
            let extractedColor = ArtworkDominantColor.extract(from: image)
            await MainActor.run {
                guard let self, self.artworkLoadToken == token else { return }
                self.nowPlayingArtwork = MPMediaItemArtwork(boundsSize: image.size) { _ in image }
                self.updateNowPlayingInfo()
                if let extractedColor {
                    self.accentColorOverride = Color(extractedColor)
                }
            }
            #endif
        }
    }

    // MARK: - Test detection

    nonisolated static let isRunningTests: Bool = {
        NSClassFromString("XCTestCase") != nil
    }()
}
