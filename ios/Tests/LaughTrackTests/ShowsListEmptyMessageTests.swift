import Foundation
import SwiftUI
import Testing
import HTTPTypes
import OpenAPIRuntime
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Search empty recovery", .serialized)
@MainActor
struct SearchEmptyRecoveryTests {
    private func location() -> NearbyLocationController {
        LaughTrackHostedViewTestSupport.makeNearbyLocationController(
            store: LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "empty-recovery")
        )
    }

    @Test("query misses offer editing while unrestricted catalogs have no reset")
    func queryAndCatalog() {
        for entity in ["comedians", "clubs", "shows"] {
            let miss = SearchEmptyState.resolve(entity: entity, query: "  Ray Devito  ")
            #expect(miss.recovery == .editSearch)
            #expect(miss.message.contains("“Ray Devito”"))
            let catalog = SearchEmptyState.resolve(entity: entity, query: " \n ")
            #expect(catalog.recovery == nil)
            #expect(!catalog.title.contains("matching"))
        }
    }

    @Test("Show recovery relaxes filters then dates without erasing names or presentation")
    func showsPreserveIntent() {
        let model = ShowsListModel(nearbyLocationController: location())
        model.comedianSearchText = "Ray Devito"
        model.clubSearchText = "Comedy Cellar"
        model.selectedFilterSlugs = ["free"]
        model.maximumPrice = .twenty
        model.sort = .latest
        model.resultsPresentation = .calendar
        model.zipCodeDraft = "10012"
        #expect(model.applyManualZip())
        let original = model.requestKey
        #expect(model.emptyState.recovery == .resetFilters)
        model.recoverFromEmpty(.resetFilters)
        #expect(model.selectedFilterSlugs.isEmpty)
        #expect(model.maximumPrice == .any)
        #expect(model.requestKey.comedian == original.comedian)
        #expect(model.requestKey.club == original.club)
        #expect(model.dateRange == original.dateRange)
        #expect(model.sort == .latest)
        #expect(model.resultsPresentation == .calendar)
        #expect(model.activeNearbyPreference?.zipCode == "10012")
        #expect(model.emptyState.recovery == .anyDate)
        model.recoverFromEmpty(.anyDate)
        #expect(!model.dateRange.isActive)
        #expect(model.emptyState.recovery == .editSearch)
        // A named comedian search is already nationwide, despite the saved ZIP.
        #expect(model.requestKey.sanitizedZip == nil)
        #expect(!model.emptyState.message.contains("miles"))
        #expect(model.comedianSearchText == "Ray Devito")
        #expect(model.clubSearchText == "Comedy Cellar")
    }

    @Test("distance expands progressively and never discards unrelated constraints")
    func distanceRecovery() {
        let model = ClubsDiscoveryModel(nearbyLocationController: location())
        model.searchText = "Comedy Cellar"
        model.sort = .leastPopular
        model.includeEmpty = true
        model.zipCodeDraft = "10012"
        #expect(model.applyManualZip())
        model.distance = .nearby
        for expected in [ShowDistanceOption.city, .regional, .roadTrip] {
            #expect(model.emptyState.recovery == .expandDistance)
            #expect(model.emptyState.message.contains("\(expected.rawValue) miles"))
            model.recoverFromEmpty(.expandDistance)
            #expect(model.distance == expected)
            #expect(model.searchText == "Comedy Cellar")
            #expect(model.activeNearbyPreference?.zipCode == "10012")
            #expect(model.sort == .leastPopular)
        }
        #expect(model.emptyState.recovery == .clearLocation)
        model.recoverFromEmpty(.clearLocation)
        #expect(model.requestKey.sanitizedZip == nil)
        #expect(model.searchText == "Comedy Cellar")
        #expect(model.includeEmpty)
        #expect(model.emptyState.recovery == .editSearch)
    }

    @Test("club availability is distinct from a true empty catalog")
    func clubAvailability() {
        let model = ClubsDiscoveryModel(nearbyLocationController: location())
        model.clearLocation()
        #expect(model.emptyState.recovery == .includeAllClubs)
        model.recoverFromEmpty(.includeAllClubs)
        #expect(model.includeEmpty)
        #expect(model.emptyState.recovery == nil)
        #expect(model.emptyState.title == "No clubs listed yet")
    }

    @Test("entity facet and home city recovery preserve query and sort")
    func entityFilters() {
        let model = ComediansDiscoveryModel()
        model.searchText = "Ray Devito"
        model.sort = .alphabetical
        model.homeCity = "New York|NY"
        model.selectedFilterSlugs = ["podcast"]
        #expect(model.emptyState.recovery == .resetFilters)
        model.recoverFromEmpty(.resetFilters)
        #expect(model.homeCity == "New York|NY")
        #expect(model.emptyState.recovery == .allHomeCities)
        model.recoverFromEmpty(.allHomeCities)
        #expect(model.homeCity == nil)
        #expect(model.searchText == "Ray Devito")
        #expect(model.sort == .alphabetical)
        #expect(model.emptyState.recovery == .editSearch)
        let clubs = ClubsDiscoveryModel(nearbyLocationController: location())
        clubs.searchText = "The Stand"
        clubs.selectedFilterSlugs = ["independent"]
        clubs.recoverFromEmpty(.resetFilters)
        #expect(clubs.selectedFilterSlugs.isEmpty)
        #expect(clubs.searchText == "The Stand")
    }

    @Test("pinned entities only offer effective recoveries")
    func pinnedSearch() {
        let model = ShowsListModel(nearbyLocationController: location(), pinnedClubId: 5,
                                   pinnedClubName: "Comedy Cellar", initialUseDateRange: false)
        model.zipCodeDraft = "10012"
        #expect(model.applyManualZip())
        #expect(model.requestKey.sanitizedZip == nil)
        #expect(model.emptyState.recovery == nil)
        #expect(model.emptyState.message.contains("Comedy Cellar"))
        model.dateRange.isActive = true
        #expect(model.emptyState.recovery == .anyDate)
        model.recoverFromEmpty(.anyDate)
        #expect(model.requestKey.clubId == 5)
        #expect(model.emptyState.recovery == nil)
    }

    @Test("Show distance recovery uses effective ZIP and preserves the club query")
    func showDistance() {
        let model = ShowsListModel(nearbyLocationController: location(), initialUseDateRange: false)
        model.clubSearchText = "The Stand"
        model.zipCodeDraft = "10012"
        #expect(model.applyManualZip())
        #expect(model.emptyState.recovery == .expandDistance)
        model.recoverFromEmpty(.expandDistance)
        #expect(model.distance == .regional)
        #expect(model.clubSearchText == "The Stand")
        model.distance = .roadTrip
        model.recoverFromEmpty(.clearLocation)
        #expect(model.requestKey.sanitizedZip == nil)
        #expect(model.clubSearchText == "The Stand")
    }
}

extension SearchEmptyRecoveryTests {
    @Test("a comedian with zero upcoming shows stays in results and can be followed")
    func zeroShowsCanBeFollowed() async throws {
        let transport = StubClientTransport { _, _, _, operation in
            let json: String
            if operation == "searchComedians" {
                json = #"{"data":[{"id":42,"uuid":"ray-devito","name":"Ray Devito","imageUrl":"","socialData":{"id":42},"showCount":0,"isFavorite":false}],"total":1,"filters":[],"homeCityFilters":[]}"#
            } else if operation == "getFavorites" {
                json = #"{"data":[{"id":42,"uuid":"ray-devito","name":"Ray Devito","imageUrl":"","socialData":{"id":42},"showCount":0,"isFavorite":true}]}"#
            } else if operation == "addFavorite" {
                json = #"{"data":{"isFavorited":true}}"#
            } else {
                Issue.record("Unexpected operation: \(operation)")
                json = #"{"error":"unexpected"}"#
            }
            return (HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]), HTTPBody(json))
        }
        let client = Client(serverURL: URL(string: "https://test.example.com")!, configuration: .laughTrack, transport: transport)
        let model = ComediansDiscoveryModel()
        model.searchText = "Ray Devito"
        let favorites = ComedianFavoriteStore()
        await model.reload(apiClient: client, favorites: favorites)
        guard case .success(let response) = model.phase else {
            Issue.record("Expected successful comedian search"); return
        }
        let comedian = try #require(response.items.first)
        #expect(response.total == 1)
        #expect(comedian.showCount == 0)
        #expect(comedian.name == "Ray Devito")
        #expect(!model.includeEmpty)
        let auth = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(name: "empty-recovery-follow")
        let result = await favorites.toggle(uuid: comedian.uuid, currentValue: false, apiClient: client, authManager: auth)
        guard case .updated(true) = result else {
            Issue.record("Expected following a comedian without scheduled shows to succeed"); return
        }
        #expect(favorites.value(for: comedian.uuid, fallback: false))
        #expect(transport.capturedRequests.map(\.operationID) == ["searchComedians", "addFavorite", "getFavorites"])
    }
}

#if canImport(UIKit)
extension SearchEmptyRecoveryTests {
    @Test("an empty response retains the selected home city until explicit recovery")
    func emptyResponseRetainsCity() async throws {
        let model = ComediansDiscoveryModel()
        model.searchText = "Ray Devito"
        model.homeCity = "New York|NY"
        let city = Components.Schemas.HomeCityFilter(value: "New York|NY", label: "New York, NY", count: 1)
        await model.reload(query: model.requestKey) { _, _ in
            .success(.init(items: [], total: 0, homeCityFilters: [city]))
        }
        let host = HostedView(
            ComediansDiscoveryView(apiClient: LaughTrackHostedViewTestSupport.makeClient(), model: model, isActive: false)
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "city-empty"))
                .environmentObject(ComedianFavoriteStore())
                .environmentObject(TypedNavigationCoordinator<AppRoute>()), freshWindow: true
        )
        await host.settle(iterations: 3)
        await model.reload(query: model.requestKey) { _, _ in .success(.init(items: [], total: 0)) }
        await host.settle(iterations: 3)
        #expect(model.homeCity == "New York|NY")
        #expect(model.emptyState.recovery == .allHomeCities)
        model.recoverFromEmpty(.allHomeCities)
        #expect(model.homeCity == nil)
        #expect(model.searchText == "Ray Devito")
    }
}
#endif
