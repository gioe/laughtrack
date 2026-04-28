import Foundation
import Testing
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Detail fetch support")
@MainActor
struct DetailFetchSupportTests {
    @Test("classifyDetailFetchError gives offline copy for notConnectedToInternet")
    func classifyOffline() {
        let failure = classifyDetailFetchError(URLError(.notConnectedToInternet), context: "comedian details")
        #expect(failure == .network("You appear to be offline. Check your connection and try again."))
    }

    @Test("classifyDetailFetchError gives timeout copy for timedOut")
    func classifyTimedOut() {
        let failure = classifyDetailFetchError(URLError(.timedOut), context: "comedian details")
        #expect(failure == .network("LaughTrack timed out while loading comedian details. Please try again."))
    }

    @Test("classifyDetailFetchError gives DNS copy for cannotFindHost")
    func classifyCannotFindHost() {
        let failure = classifyDetailFetchError(URLError(.cannotFindHost), context: "club details")
        #expect(failure == .network("LaughTrack couldn't find the club details service. Please try again in a moment."))
    }

    @Test("classifyDetailFetchError falls back to generic copy for other URLError codes")
    func classifyOtherURLError() {
        let failure = classifyDetailFetchError(URLError(.badServerResponse), context: "club details")
        #expect(failure == .network("LaughTrack couldn't reach the club details service. Check your connection and try again."))
    }

    @Test("classifyDetailFetchError falls back to generic copy for non-URLError errors")
    func classifyNonURLError() {
        struct OtherError: Error {}
        let failure = classifyDetailFetchError(OtherError(), context: "comedian details")
        #expect(failure == .network("LaughTrack couldn't reach the comedian details service. Check your connection and try again."))
    }

    @Test("withDetailFetchRetry retries once on a transient URLError and returns the second result")
    func retryOnTransient() async throws {
        var attempts = 0
        let result = try await withDetailFetchRetry(backoff: .milliseconds(1)) {
            attempts += 1
            if attempts == 1 {
                throw URLError(.timedOut)
            }
            return "ok"
        }
        #expect(result == "ok")
        #expect(attempts == 2)
    }

    @Test("withDetailFetchRetry rethrows the second failure when the retry also fails")
    func rethrowsAfterRetry() async {
        var attempts = 0
        do {
            _ = try await withDetailFetchRetry(backoff: .milliseconds(1)) { () -> String in
                attempts += 1
                throw URLError(.cannotFindHost)
            }
            Issue.record("Expected withDetailFetchRetry to rethrow")
        } catch let error as URLError {
            #expect(error.code == .cannotFindHost)
            #expect(attempts == 2)
        } catch {
            Issue.record("Expected URLError, got \(error)")
        }
    }

    @Test("withDetailFetchRetry does not retry non-transient URLError codes")
    func doesNotRetryNonTransient() async {
        var attempts = 0
        do {
            _ = try await withDetailFetchRetry(backoff: .milliseconds(1)) { () -> String in
                attempts += 1
                throw URLError(.badURL)
            }
            Issue.record("Expected withDetailFetchRetry to rethrow")
        } catch let error as URLError {
            #expect(error.code == .badURL)
            #expect(attempts == 1)
        } catch {
            Issue.record("Expected URLError, got \(error)")
        }
    }

    @Test("withDetailFetchRetry does not retry non-URLError throws")
    func doesNotRetryNonURLError() async {
        struct OtherError: Error {}
        var attempts = 0
        do {
            _ = try await withDetailFetchRetry(backoff: .milliseconds(1)) { () -> String in
                attempts += 1
                throw OtherError()
            }
            Issue.record("Expected withDetailFetchRetry to rethrow")
        } catch is OtherError {
            #expect(attempts == 1)
        } catch {
            Issue.record("Expected OtherError, got \(error)")
        }
    }
}
