import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Date range density entity scoping and per-month cache")
struct DateRangeDensityTests {
    @Test("compute forwards a pinned comedian even when preference is nil")
    func computeForwardsComedianWithoutPreference() async {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            var response = HTTPResponse(status: .ok)
            response.headerFields[.contentType] = "application/json"
            return (response, HTTPBody("{}"))
        }
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: transport
        )

        let result = await DateRangeDensity.compute(
            preference: nil,
            comedian: "Akaash Singh",
            fromDate: Date(),
            now: Date(),
            apiClient: apiClient
        )

        // Entity scoping must short-circuit the no-preference early return so
        // detail-page calendars paint their entity's full dot map even when
        // the user has no zip set.
        #expect(result == [:])
        #expect(transport.capturedRequests.count == 1)
        let path = transport.capturedRequests.first?.path ?? ""
        #expect(path.contains("comedian=Akaash%20Singh"))
        #expect(!path.contains("club="))
    }

    @Test("compute forwards a pinned club even when preference is nil")
    func computeForwardsClubWithoutPreference() async {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            var response = HTTPResponse(status: .ok)
            response.headerFields[.contentType] = "application/json"
            return (response, HTTPBody("{}"))
        }
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: transport
        )

        let result = await DateRangeDensity.compute(
            preference: nil,
            club: "Comedy Cellar",
            fromDate: Date(),
            now: Date(),
            apiClient: apiClient
        )

        // Club-pinned views (e.g. ClubDetailView) disable location filtering;
        // the density call must still go out with the club scope so the
        // calendar paints that venue's dot map.
        #expect(result == [:])
        #expect(transport.capturedRequests.count == 1)
        let path = transport.capturedRequests.first?.path ?? ""
        #expect(path.contains("club=Comedy%20Cellar"))
        #expect(!path.contains("comedian="))
    }

    @Test("compute returns empty without hitting the network when preference, comedian, and club are all nil")
    func computeReturnsEmptyWithoutAnyScope() async {
        let transport = StubClientTransport.alwaysFails()
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: transport
        )

        let result = await DateRangeDensity.compute(
            preference: nil,
            fromDate: Date(),
            now: Date(),
            apiClient: apiClient
        )

        // Preserves the pre-existing "no scope → no dots, no network" contract
        // that the search-tab sheet relies on before the user picks a zip.
        #expect(result == [:])
        #expect(transport.capturedRequests.isEmpty)
    }

    @Test("compute respects an explicit toDate and emits matching from/to query params")
    func computeUsesExplicitToDateForPerMonthWindows() async {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            var response = HTTPResponse(status: .ok)
            response.headerFields[.contentType] = "application/json"
            return (response, HTTPBody("{}"))
        }
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: transport
        )

        // Pin both endpoints far enough in the future that the `max(anchor, today)`
        // clamp inside compute can't shorten the from-date; the test asserts the
        // exact day-window callers pass — this is the contract that the cache
        // key (monthStart) and the fetch window stay aligned on.
        let calendar = Calendar.current
        let from = calendar.date(from: DateComponents(year: 2030, month: 7, day: 1))!
        let to = calendar.date(from: DateComponents(year: 2030, month: 7, day: 31))!

        let result = await DateRangeDensity.compute(
            preference: nil,
            comedian: "Hannibal Buress",
            fromDate: from,
            toDate: to,
            now: from,
            apiClient: apiClient
        )

        #expect(result == [:])
        #expect(transport.capturedRequests.count == 1)
        let path = transport.capturedRequests.first?.path ?? ""
        #expect(path.contains("from=2030-07-01"))
        #expect(path.contains("to=2030-07-31"))
    }

    @Test("cache: revisiting a fetched month with the same signature is a hit, not a fetch")
    func cacheRevisitIsHit() async {
        let monthA = Calendar.current.startOfDay(for: Date())
        let monthB = Calendar.current.date(byAdding: .month, value: 1, to: monthA)!

        var state = DateRangeDensityCacheState()
        var fetchCalls = 0

        @discardableResult
        func loadIfNeeded(monthStart: Date, signature: String) async -> Bool {
            guard state.needsFetch(monthStart: monthStart, signature: signature) else {
                return false
            }
            fetchCalls += 1
            state.storeIfSignatureMatches([:], forMonthStart: monthStart, signature: signature)
            return true
        }

        #expect(await loadIfNeeded(monthStart: monthA, signature: "sig1"))
        #expect(fetchCalls == 1)
        #expect(await loadIfNeeded(monthStart: monthB, signature: "sig1"))
        #expect(fetchCalls == 2)

        // Revisiting monthA with the same signature must NOT call fetch — this
        // is the "swipe forward, swipe back, no duplicate request" guarantee.
        #expect(!(await loadIfNeeded(monthStart: monthA, signature: "sig1")))
        #expect(fetchCalls == 2)
    }

    @Test("cache: signature change clears entries so a stale dot map cannot leak across scopes")
    func cacheSignatureChangeInvalidates() {
        let monthA = Calendar.current.startOfDay(for: Date())

        var state = DateRangeDensityCacheState()
        _ = state.needsFetch(monthStart: monthA, signature: "sig1")
        state.storeIfSignatureMatches([monthA: 3], forMonthStart: monthA, signature: "sig1")
        #expect(state.entries[monthA] == [monthA: 3])

        // A signature change models the user editing zip / distance / entity
        // scope while the sheet is open; stale dots from the old scope must
        // not survive into the new scope.
        let needsRefetch = state.needsFetch(monthStart: monthA, signature: "sig2")
        #expect(needsRefetch)
        #expect(state.entries.isEmpty)
        #expect(state.signature == "sig2")
    }

    @Test("cache: post-await write is dropped when a concurrent loader changed the signature")
    func cacheStaleWriteIsDroppedAfterSignatureChange() {
        let monthA = Calendar.current.startOfDay(for: Date())

        var state = DateRangeDensityCacheState()
        // Loader A starts under sig1, sees the cache miss.
        _ = state.needsFetch(monthStart: monthA, signature: "sig1")

        // Loader B runs and changes the signature mid-await for Loader A.
        _ = state.needsFetch(monthStart: monthA, signature: "sig2")

        // Loader A returns from its await and tries to store the stale entry.
        // The signature mismatch must drop the write — otherwise the new
        // (sig2) scope would inherit a row from the old (sig1) scope.
        state.storeIfSignatureMatches([monthA: 9], forMonthStart: monthA, signature: "sig1")

        #expect(state.entries[monthA] == nil)
        #expect(state.signature == "sig2")
    }
}
