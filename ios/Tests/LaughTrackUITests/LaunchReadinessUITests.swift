import Foundation
import Network
import XCTest

/// Runs the real application against a local server that withholds responses or
/// returns a failure. Navigation must work while Discover is loading or retrying.
/// No mock-mode root, external fixture process, or populated feed cache is used.
@MainActor
final class LaunchReadinessUITests: XCTestCase {
    private let loadingLogoID = "laughtrack.launch.loading-logo"

    func testColdGuestCanSearchAndResumeWhileFeedIsPending() throws {
        continueAfterFailure = false
        let server = try HeldLaunchServer()
        defer { server.stop() }
        wait(for: [server.ready], timeout: 5)

        let app = configuredApp(server: server, guest: true)
        defer { app.terminate() }
        app.launch()

        wait(for: [server.feedRequested], timeout: 10)
        attachScreenshot(app, named: "Returning guest — feed pending")
        assertSearchIsUsable(app)
        attachScreenshot(app, named: "Search — feed pending")

        XCUIDevice.shared.press(.home)
        XCTAssertTrue(app.wait(for: .runningBackground, timeout: 5))
        app.activate()

        XCTAssertTrue(app.tabBars.buttons["Search"].isSelected, "Resume must retain the selected tab")
        XCTAssertTrue(app.descendants(matching: .any)["laughtrack.shows-search.screen"].firstMatch.exists)
        XCTAssertFalse(loadingLogo(in: app).exists, "An ordinary resume must not replay the launch overlay")
        attachScreenshot(app, named: "Search — resumed")
    }

    func testFirstEntryGuestChoiceOpensUsableShellBeforeFeedResponds() throws {
        continueAfterFailure = false
        let server = try HeldLaunchServer()
        defer { server.stop() }
        wait(for: [server.ready], timeout: 5)

        let app = configuredApp(server: server, guest: false)
        defer { app.terminate() }
        app.launch()

        let guest = app.buttons["Continue as guest"]
        XCTAssertTrue(guest.waitForExistence(timeout: 10))
        XCTAssertTrue(guest.isHittable, "First-entry choice must be usable without feed data")
        XCTAssertFalse(loadingLogo(in: app).exists)
        attachScreenshot(app, named: "First-entry choice")
        guest.tap()

        wait(for: [server.feedRequested], timeout: 10)
        attachScreenshot(app, named: "Guest choice — feed pending")
        assertSearchIsUsable(app)
    }

    func testFailedFeedCanRetryWithoutBlockingNavigation() throws {
        continueAfterFailure = false
        let server = try HeldLaunchServer(mode: .unavailable)
        defer { server.stop() }
        wait(for: [server.ready], timeout: 5)

        let app = configuredApp(server: server, guest: true)
        defer { app.terminate() }
        app.launch()
        wait(for: [server.feedRequested], timeout: 10)

        let retry = app.buttons["Try again"].firstMatch
        XCTAssertTrue(retry.waitForExistence(timeout: 10), "A failed feed must expose its recovery action")
        XCTAssertTrue(retry.isHittable)
        XCTAssertFalse(loadingLogo(in: app).exists, "A failed feed must not retain the launch overlay")
        attachScreenshot(app, named: "Discover — service unavailable")

        let retriedFeed = server.holdNextFeedRequest()
        retry.tap()
        wait(for: [retriedFeed], timeout: 5)
        attachScreenshot(app, named: "Discover — retry pending")
        assertSearchIsUsable(app)
    }

    func testNativeReduceMotionFirstEntryAndLiveGuestHandoff() throws {
        continueAfterFailure = false
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        settings.launch()
        for _ in 0..<5 { settings.swipeDown() }
        let accessibility = settings.staticTexts["Accessibility"].firstMatch
        for _ in 0..<8 where !accessibility.isHittable { settings.swipeUp() }
        XCTAssertTrue(accessibility.waitForExistence(timeout: 5))
        accessibility.tap()
        settings.staticTexts["Motion"].firstMatch.tap()
        let toggle = settings.switches["Reduce Motion"]
        XCTAssertTrue(toggle.waitForExistence(timeout: 5))
        let originallyEnabled = toggle.value as? String == "1"
        if !originallyEnabled { toggle.tap() }
        XCTAssertEqual(toggle.value as? String, "1")
        defer {
            settings.activate()
            if (toggle.value as? String == "1") != originallyEnabled { toggle.tap() }
            settings.terminate()
        }

        let server = try HeldLaunchServer()
        defer { server.stop() }
        wait(for: [server.ready], timeout: 5)
        let app = configuredApp(server: server, guest: false)
        defer { app.terminate() }
        app.launch()
        let guest = app.buttons["Continue as guest"]
        XCTAssertTrue(guest.waitForExistence(timeout: 10))
        attachScreenshot(app, named: "Native Reduce Motion — first entry")
        app.buttons["Continue with Apple"].tap()
        let cancel = XCUIApplication(bundleIdentifier: "com.apple.springboard").buttons["Cancel"].firstMatch
        XCTAssertTrue(cancel.waitForExistence(timeout: 10), "Authentication must provide a cancellation action")
        attachScreenshot(app, named: "Native Reduce Motion — signing in")
        cancel.tap()
        XCTAssertTrue(guest.waitForExistence(timeout: 10))
        attachScreenshot(app, named: "Native Reduce Motion — cancelled sign in")
        guest.tap()
        wait(for: [server.feedRequested], timeout: 10)
        attachScreenshot(app, named: "Native Reduce Motion — guest handoff")
        assertSearchIsUsable(app)

        // Change the native preference while this app remains alive.
        settings.activate()
        toggle.tap()
        XCTAssertEqual(toggle.value as? String, "0")
        app.activate()
        XCTAssertTrue(app.tabBars.buttons["Search"].isSelected)
        attachScreenshot(app, named: "Reduce Motion disabled live — Search retained")
        settings.activate()
        toggle.tap()
        XCTAssertEqual(toggle.value as? String, "1")
        app.activate()
        XCTAssertTrue(app.tabBars.buttons["Search"].isSelected)
        XCTAssertFalse(loadingLogo(in: app).exists)
        attachScreenshot(app, named: "Reduce Motion re-enabled live — Search retained")
    }

    private func attachScreenshot(_ app: XCUIApplication, named name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func configuredApp(server: HeldLaunchServer, guest: Bool) -> XCUIApplication {
        let app = XCUIApplication()
        // Includes the persisted feed cache; otherwise a previous screenshot run
        // could satisfy the old feed-gated launch overlay and mask the regression.
        app.launchArguments = [UITestLaunchArgs.resetState]
        if guest { app.launchArguments.append(UITestLaunchArgs.guestBrowsing) }
        app.launchEnvironment["LAUGHTRACK_API_BASE_URL"] = server.baseURL
        return app
    }

    private func assertSearchIsUsable(
        _ app: XCUIApplication,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let search = app.tabBars.buttons["Search"]
        XCTAssertTrue(search.waitForExistence(timeout: 5), file: file, line: line)
        XCTAssertTrue(search.isHittable, "Feed loading must not cover tab controls", file: file, line: line)
        XCTAssertFalse(loadingLogo(in: app).exists, "The shell must not retain a feed-dependent splash", file: file, line: line)
        search.tap()
        XCTAssertTrue(
            app.descendants(matching: .any)["laughtrack.shows-search.screen"].firstMatch.waitForExistence(timeout: 5),
            "Search must actually open while the server is withholding every response",
            file: file,
            line: line
        )
        XCTAssertTrue(search.isSelected, file: file, line: line)
    }

    private func loadingLogo(in app: XCUIApplication) -> XCUIElement {
        app.descendants(matching: .any)[loadingLogoID].firstMatch
    }
}

/// Owns an ephemeral loopback port for one test. Pending requests stay open
/// without a response, including retries, so there is no artificial-delay race.
/// The unavailable mode returns 503 to exercise recovery. Mutable state stays
/// on `queue`.
private final class HeldLaunchServer: @unchecked Sendable {
    enum Mode {
        case held
        case unavailable
    }

    let ready = XCTestExpectation(description: "Loopback launch server ready")
    let feedRequested = XCTestExpectation(description: "Real application requested home/feed")

    private let queue = DispatchQueue(label: "laughtrack.tests.held-launch-server")
    private let listener: NWListener
    private var connections: [NWConnection] = []
    private var sawFeedRequest = false
    private var mode: Mode
    private var nextFeedRequest: XCTestExpectation?

    var baseURL: String {
        "http://127.0.0.1:\(listener.port!.rawValue)"
    }

    init(mode: Mode = .held) throws {
        self.mode = mode
        listener = try NWListener(using: .tcp, on: .any)
        listener.stateUpdateHandler = { [weak self] state in
            if case .ready = state { self?.ready.fulfill() }
        }
        listener.newConnectionHandler = { [weak self] connection in
            guard let self else { return }
            connections.append(connection)
            connection.start(queue: queue)
            receiveHeaders(from: connection, accumulated: Data())
        }
        listener.start(queue: queue)
    }

    func holdNextFeedRequest() -> XCTestExpectation {
        let request = XCTestExpectation(description: "Try again issued a new home/feed request")
        queue.sync {
            mode = .held
            nextFeedRequest = request
        }
        return request
    }

    func stop() {
        queue.sync {
            listener.cancel()
            connections.forEach { $0.cancel() }
            connections.removeAll()
        }
    }

    private func receiveHeaders(from connection: NWConnection, accumulated: Data) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 16_384) { [weak self] data, _, complete, error in
            guard let self else { return }
            var headers = accumulated
            if let data { headers.append(data) }
            let text = String(decoding: headers, as: UTF8.self)
            if text.contains("\r\n\r\n") {
                if text.components(separatedBy: "\r\n").first?.contains("/home/feed") == true {
                    if !sawFeedRequest {
                        sawFeedRequest = true
                        feedRequested.fulfill()
                    }
                    nextFeedRequest?.fulfill()
                    nextFeedRequest = nil
                }
                if mode == .unavailable {
                    let body = "{\"error\":\"Service unavailable\"}"
                    let response = "HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\nContent-Length: \(body.utf8.count)\r\nConnection: close\r\n\r\n\(body)"
                    connection.send(content: Data(response.utf8), completion: .contentProcessed { _ in
                        connection.cancel()
                    })
                }
                // Held mode intentionally retains the connection without replying.
            } else if !complete, error == nil, headers.count < 65_536 {
                receiveHeaders(from: connection, accumulated: headers)
            }
        }
    }
}
