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

    @Test("cache: revisiting a fetched month with the same signature is a hit, not a fetch")
    func cacheRevisitIsHit() async {
        let monthA = Calendar.current.startOfDay(for: Date())
        let monthB = Calendar.current.date(byAdding: .month, value: 1, to: monthA)!

        var state = DateRangeDensityCacheState()
        var fetchCalls = 0
        let fetch: () async -> [Date: Int]? = {
            fetchCalls += 1
            return [:]
        }

        var didFetch: Bool
        (state, didFetch) = await DateRangeDensityCache.ensureLoaded(
            monthStart: monthA, signature: "sig1", state: state, fetch: fetch
        )
        #expect(didFetch)
        #expect(fetchCalls == 1)

        (state, didFetch) = await DateRangeDensityCache.ensureLoaded(
            monthStart: monthB, signature: "sig1", state: state, fetch: fetch
        )
        #expect(didFetch)
        #expect(fetchCalls == 2)

        // Revisiting monthA with the same signature must NOT call fetch — this
        // is the "swipe forward, swipe back, no duplicate request" guarantee.
        (state, didFetch) = await DateRangeDensityCache.ensureLoaded(
            monthStart: monthA, signature: "sig1", state: state, fetch: fetch
        )
        #expect(!didFetch)
        #expect(fetchCalls == 2)
    }

    @Test("cache: signature change clears entries so a stale dot map cannot leak across scopes")
    func cacheSignatureChangeInvalidates() async {
        let monthA = Calendar.current.startOfDay(for: Date())

        var state = DateRangeDensityCacheState()
        var fetchCalls = 0
        let fetch: () async -> [Date: Int]? = {
            fetchCalls += 1
            return [:]
        }

        (state, _) = await DateRangeDensityCache.ensureLoaded(
            monthStart: monthA, signature: "sig1", state: state, fetch: fetch
        )
        #expect(fetchCalls == 1)

        // A signature change models the user editing zip / distance / entity
        // scope while the sheet is open; stale dots from the old scope must
        // not survive into the new scope.
        let result = await DateRangeDensityCache.ensureLoaded(
            monthStart: monthA, signature: "sig2", state: state, fetch: fetch
        )
        #expect(result.didFetch)
        #expect(fetchCalls == 2)
        #expect(result.state.signature == "sig2")
    }

    @Test("cache: nil fetch result is not stored so the next visit retries the network")
    func cacheDoesNotCacheNilFetch() async {
        let monthA = Calendar.current.startOfDay(for: Date())

        var state = DateRangeDensityCacheState()
        var fetchCalls = 0
        let nilFetch: () async -> [Date: Int]? = {
            fetchCalls += 1
            return nil
        }

        (state, _) = await DateRangeDensityCache.ensureLoaded(
            monthStart: monthA, signature: "sig1", state: state, fetch: nilFetch
        )
        #expect(fetchCalls == 1)
        // Revisiting after a nil result must try the network again — caching
        // a transient failure would mask the recovery once the network came
        // back, and would also poison the merged dot map with nothing.
        let result = await DateRangeDensityCache.ensureLoaded(
            monthStart: monthA, signature: "sig1", state: state, fetch: nilFetch
        )
        #expect(result.didFetch)
        #expect(fetchCalls == 2)
    }
}
