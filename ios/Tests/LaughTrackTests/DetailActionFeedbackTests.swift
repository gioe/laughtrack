import Testing
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Detail action feedback")
@MainActor
struct DetailActionFeedbackTests {
    @Test("favorite success uses the server-returned state for every entity", arguments: [true, false])
    func favoriteSuccess(_ isFavorite: Bool) {
        let expected = DetailActionFeedback.toast(
            isFavorite ? "Saved Taylor to favorites." : "Removed Taylor from favorites."
        )
        #expect(DetailActionFeedback.favorite(ComedianFavoriteStore.ToggleResult.updated(isFavorite), name: "Taylor") == expected)
        #expect(DetailActionFeedback.favorite(ClubFavoriteStore.ToggleResult.updated(isFavorite), name: "Taylor") == expected)
        #expect(DetailActionFeedback.favorite(PodcastFavoriteStore.ToggleResult.updated(isFavorite), name: "Taylor") == expected)
    }

    @Test("saved show success distinguishes saving and removal", arguments: [true, false])
    func savedShowSuccess(_ isSaved: Bool) {
        let expected = DetailActionFeedback.toast(
            isSaved ? "Saved to your Library." : "Removed from your Library."
        )
        #expect(DetailActionFeedback.savedShow(.updated(isSaved)) == expected)
    }

    @Test("offline save and removal explain that synchronization is pending", arguments: [true, false])
    func queuedShowMutation(_ isSaved: Bool) {
        let expected = DetailActionFeedback.toast(
            isSaved
                ? "Saved offline. We’ll sync when you’re connected."
                : "Removal saved offline. We’ll sync when you’re connected."
        )
        #expect(DetailActionFeedback.savedShow(.queued(isSaved)) == expected)
        #expect(DetailActionFeedback.savedShow(.queued(isSaved)) != DetailActionFeedback.savedShow(.updated(isSaved)))
    }

    @Test("every favorite and save failure retains its actionable message")
    func failures() {
        let message = "Couldn’t save this item. Please try again."
        let expected = DetailActionFeedback.alert(message)
        #expect(DetailActionFeedback.favorite(ComedianFavoriteStore.ToggleResult.failure(message), name: "Taylor") == expected)
        #expect(DetailActionFeedback.favorite(ClubFavoriteStore.ToggleResult.failure(message), name: "Taylor") == expected)
        #expect(DetailActionFeedback.favorite(PodcastFavoriteStore.ToggleResult.failure(message), name: "Taylor") == expected)
        #expect(DetailActionFeedback.savedShow(.failure(message)) == expected)
    }

    @Test("every favorite and save authorization result requests sign-in")
    func signInRequired() {
        #expect(DetailActionFeedback.favorite(ComedianFavoriteStore.ToggleResult.signInRequired("Sign in"), name: "Taylor") == .signIn)
        #expect(DetailActionFeedback.favorite(ClubFavoriteStore.ToggleResult.signInRequired("Sign in"), name: "Taylor") == .signIn)
        #expect(DetailActionFeedback.favorite(PodcastFavoriteStore.ToggleResult.signInRequired("Sign in"), name: "Taylor") == .signIn)
        #expect(DetailActionFeedback.savedShow(.signInRequired("Sign in")) == .signIn)
    }

    @Test("repeated success replaces the banner and announces each completed action")
    func repeatedSuccessPresentation() throws {
        let manager = ToastManager()
        defer { manager.dismiss() }
        var announcements: [String] = []
        var alerts: [String] = []
        var signIns = 0
        let message = "Saved Taylor to favorites."
        let feedback = DetailActionFeedback.toast(message)

        feedback.present(using: manager, signIn: { signIns += 1 }, alert: { alerts.append($0) }, announce: { announcements.append($0) })
        let first = try #require(manager.currentToast)
        #expect(first.message == message)

        feedback.present(using: manager, signIn: { signIns += 1 }, alert: { alerts.append($0) }, announce: { announcements.append($0) })
        let second = try #require(manager.currentToast)
        #expect(second.id != first.id)
        #expect(second.message == message)
        #expect(announcements == [message, message])
        #expect(alerts.isEmpty)
        #expect(signIns == 0)
    }

    @Test("errors and sign-in preserve their existing presentation without success feedback")
    func nonSuccessPresentation() {
        let manager = ToastManager()
        defer { manager.dismiss() }
        var announcements: [String] = []
        var alerts: [String] = []
        var signIns = 0
        manager.show("Earlier success", type: .info)
        DetailActionFeedback.alert("Please try again.").present(
            using: manager, signIn: { signIns += 1 }, alert: { alerts.append($0) }, announce: { announcements.append($0) }
        )
        #expect(manager.currentToast == nil)
        #expect(alerts == ["Please try again."])
        #expect(signIns == 0)
        #expect(announcements.isEmpty)

        manager.show("Earlier success", type: .info)
        DetailActionFeedback.signIn.present(
            using: manager, signIn: { signIns += 1 }, alert: { alerts.append($0) }, announce: { announcements.append($0) }
        )
        #expect(manager.currentToast == nil)
        #expect(alerts == ["Please try again."])
        #expect(signIns == 1)
        #expect(announcements.isEmpty)
    }

    @Test("the app resolves the same toast manager for the banner and detail actions")
    func toastManagerIsShared() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)
        let presenter = container.resolve(ToastManager.self)
        let action = container.resolve(ToastManager.self)
        defer { presenter.dismiss() }
        #expect(presenter === action)
        action.show("Saved to your Library.", type: .info)
        #expect(presenter.currentToast?.message == "Saved to your Library.")
        presenter.dismiss()
        #expect(action.currentToast == nil)
    }
}

#if canImport(UIKit)
import SwiftUI
import UIKit
import Vision

@Suite("Detail feedback navigation", .serialized)
@MainActor
struct DetailFeedbackNavigationTests {
    @Test("the rendered success banner survives push and pop without an alert", arguments: [false, true])
    func bannerSurvivesNavigation(_ accessibility: Bool) async throws {
        let manager = ToastManager()
        defer { manager.dismiss() }
        let coordinator = TypedNavigationCoordinator<AppRoute>()
        let host = HostedView(
            DetailFeedbackNavigationHarness(coordinator: coordinator, manager: manager)
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.horizontalSizeClass, .compact)
                .environment(\.dynamicTypeSize, accessibility ? .accessibility3 : .large),
            freshWindow: true, viewportSize: CGSize(width: 375, height: 812)
        )
        await host.settle()
        var alerts: [String] = []
        var announcements: [String] = []
        var signIns = 0
        let feedback = DetailActionFeedback.toast("Saved Taylor to favorites.")
        func present() {
            feedback.present(using: manager, signIn: { signIns += 1 }, alert: { alerts.append($0) }, announce: { announcements.append($0) })
        }
        let profile = accessibility ? "accessibility" : "default"

        present()
        await host.settle(iterations: 12)
        try assertVisible(host: host, profile: profile, stage: "root")
        let firstID = try #require(manager.currentToast?.id)

        // Repeating a completed action replaces the banner, but navigation itself
        // must preserve the same mounted presentation and message identity.
        present()
        let pushedID = try #require(manager.currentToast?.id)
        #expect(pushedID != firstID)
        coordinator.push(.comedianDetail(101))
        await host.settle(iterations: 20)
        #expect(coordinator.routes.count == 1)
        #expect(manager.currentToast?.id == pushedID)
        try assertVisible(host: host, profile: profile, stage: "detail")

        present()
        let returningID = try #require(manager.currentToast?.id)
        coordinator.pop()
        await host.settle(iterations: 20)
        #expect(coordinator.routes.isEmpty)
        #expect(manager.currentToast?.id == returningID)
        try assertVisible(host: host, profile: profile, stage: "returned")
        #expect(announcements == Array(repeating: "Saved Taylor to favorites.", count: 3))
        #expect(alerts.isEmpty)
        #expect(signIns == 0)
    }

    private func assertVisible(host: HostedView, profile: String, stage: String) throws {
        let image = try host.snapshot()
        #expect(image.size == CGSize(width: 375, height: 812))
        let output = FileManager.default.temporaryDirectory.appendingPathComponent("task4029-\(profile)-\(stage).png")
        try #require(image.pngData()).write(to: output)
        print("Detail feedback capture: \(output.path)")

        // Inspect rendered pixels instead of simulator accessibility lookups,
        // which are unreliable in this test host. A retained manager alone is
        // insufficient: the actual banner must still be visible after a push.
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = ["en-US"]
        request.usesLanguageCorrection = false
        let handler = VNImageRequestHandler(cgImage: try #require(image.cgImage), options: [:])
        try handler.perform([request])
        let visibleText = (request.results ?? [])
            .compactMap { $0.topCandidates(1).first?.string }
            .joined(separator: " ")
            .lowercased()
        #expect(visibleText.contains("saved taylor to favorites"), "Rendered banner missing after \(stage): \(visibleText)")
    }
}

private struct DetailFeedbackNavigationHarness: View {
    @ObservedObject var coordinator: TypedNavigationCoordinator<AppRoute>
    @ObservedObject var manager: ToastManager

    var body: some View {
        TypedCoordinatedNavigationStack(coordinator: coordinator) { _ in
            ScrollView {
                MarqueeHero(title: "Taylor on stage", imageURL: "", showsThumbnail: false)
                Text("Upcoming shows")
                    .font(.title2)
                ForEach(0..<8) { index in
                    Text("Comedy show \(index + 1)")
                        .frame(maxWidth: .infinity, minHeight: 60, alignment: .leading)
                        .padding(.horizontal)
                }
            }
        } root: {
            VStack(spacing: 24) {
                Text("Discover").font(.largeTitle)
                Button("Open Taylor") { coordinator.push(.comedianDetail(101)) }
                Spacer()
            }
            .padding()
        }
        .modifier(DetailActionFeedbackOverlay(manager: manager, clearsRootTabBar: coordinator.routes.isEmpty))
        // Mirrors the outer persistent player region without introducing audio
        // or network dependencies into a navigation-presentation regression.
        .safeAreaInset(edge: .bottom) {
            Text("Player controls remain available")
                .font(.caption)
                .frame(maxWidth: .infinity, minHeight: 64)
                .background(Color.gray.opacity(0.2))
        }
    }
}
#endif
