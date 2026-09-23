import Foundation
import Testing
import SwiftUI
import HTTPTypes
import OpenAPIRuntime
import LaughTrackBridge
import LaughTrackCore
import LaughTrackAPIClient
@testable import LaughTrackApp

#if canImport(UIKit)
@Suite("Search query visual capture", .serialized)
@MainActor
struct SearchQueryVisualCaptureTests {
    @Test("capture live category inputs at standard and accessibility sizes")
    func captureCategories() async throws {
        for size in [DynamicTypeSize.large, .accessibility5] {
            for pivot in SearchRootModel.Pivot.allCases {
                let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "query-capture")
                let store = container.resolve(NearbyPreferenceStore.self)
                store.setManualZip("10012", distanceMiles: 25)
                let host = HostedView(
                    SearchRootView(
                        apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                        favorites: ComedianFavoriteStore(),
                        coordinator: TypedNavigationCoordinator<AppRoute>(),
                        searchNavigationBridge: SearchNavigationBridge(),
                        nearbyLocationController: container.resolve(NearbyLocationController.self),
                        nearbyPreferenceStore: store,
                        isActive: false,
                        selectedPrimitive: .constant(pivot)
                    )
                    .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
                    .environment(\.appTheme, LaughTrackTheme())
                    .environment(\.dynamicTypeSize, size)
                    .environment(\.serviceContainer, container)
                    .environmentObject(ClubFavoriteStore())
                    .environmentObject(PodcastFavoriteStore())
                    .environmentObject(PodcastPlaybackController())
                    .preferredColorScheme(.dark), freshWindow: true
                )
                await host.settle(iterations: 3)
                let data = try #require(try host.snapshot().pngData())
                let textSize = size.isAccessibilitySize ? "AX5" : "standard"
                let path = FileManager.default.temporaryDirectory.appendingPathComponent("task4002-\(pivot.rawValue)-\(textSize).png")
                try data.write(to: path)
                print("Search query capture: \(path.path)")
                #if compiler(>=6.2)
                Attachment.record(Array(data), named: path.lastPathComponent)
                #endif
            }
        }
    }
}
#endif

@Suite("Shows list view presentation")
struct ShowsListViewPresentationTests {
    @Test("performer relevance requires a unique full comedian name and canonical identity")
    @MainActor
    func performerSearchRelevance() {
        let canonical = Components.Schemas.ComedianLineup(name: "J Valentino", imageUrl: "", uuid: "j", id: 1)
        let alias = Components.Schemas.ComedianLineup(name: "Jay Valentino", imageUrl: "invalid", uuid: "alias", id: 2, parentComedian: canonical)
        var show = makeShow(id: 99)
        show.lineup = [canonical, alias]
        #expect(ShowsListModel.searchPerformerContext(for: show, comedianQuery: "  j   VALENTINO ") == .searchMatch(1))
        #expect(ShowsListModel.searchPerformerContext(for: show, comedianQuery: "Jay Valentino") == .searchMatch(1))
        for query in ["", "comedy", "J", "Valentino", "Unknown Person"] {
            #expect(ShowsListModel.searchPerformerContext(for: show, comedianQuery: query) == nil)
        }
        show.lineup?.append(.init(name: "J Valentino", imageUrl: "", uuid: "other", id: 3))
        #expect(ShowsListModel.searchPerformerContext(for: show, comedianQuery: "J Valentino") == nil)
        show.lineup = nil
        #expect(ShowsListModel.searchPerformerContext(for: show, comedianQuery: "J Valentino") == nil)
    }

    #if canImport(UIKit)
    @Test("retained results do not claim a new or failed comedian query")
    @MainActor
    func retainedResultsHaveNoNewRelevance() async {
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "performer-relevance")
        let model = ShowsListModel(
            nearbyLocationController: LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store),
            initialUseDateRange: false, startsWithNearbyLocation: false
        )
        var show = makeShow(id: 99)
        show.lineup = [.init(name: "J Valentino", imageUrl: "", uuid: "j", id: 1)]
        await model.reload(query: model.requestKey) { _, _ in .success(.init(items: [show], total: 1)) }
        model.comedianSearchText = "J Valentino"
        #expect(model.performerContext(for: show) == nil)
        await model.reload(query: model.requestKey) { _, _ in .failure(.unexpected(status: 500, message: "Failed")) }
        #expect(model.performerContext(for: show) == nil)
        await model.reload(query: model.requestKey) { _, _ in .success(.init(items: [show], total: 1)) }
        #expect(model.performerContext(for: show) == .searchMatch(1))
        model.comedianSearchText = ""
        #expect(model.performerContext(for: show) == nil)
    }
    #endif

    @Test("compact pinned lists label upcoming shows with subordinate filters")
    func compactPinnedListsUseUpcomingShowsHeading() throws {
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)

        #expect(ShowsListChromeVisibility(compactMode: true).sectionTitle == "Upcoming shows")
        #expect(ShowsListChromeVisibility(compactMode: false).sectionTitle == nil)
        #expect(!source.contains("LaughTrackSectionHeader(eyebrow: \"Calendar\""))
        #expect(source.contains("if compactMode, pageCount > 1"))
        let compact = ShowsListChromeVisibility(compactMode: true)
        #expect(!compact.showsResultsStatus(for: .confirmed))
        #expect(compact.showsResultsStatus(for: .updating))
        #expect(compact.showsResultsStatus(for: .failed(.network("Offline"))))
        #expect(ShowsListChromeVisibility(compactMode: false).showsResultsStatus(for: .confirmed))
        #expect(source.contains("LaughTrackPagedControls("))
        #expect(source.contains("if !compactMode, result.canLoadMore"))
        #expect(source.contains("await model.loadPage("))
    }

    @Test("show search results use compact ticket row presentation")
    func showSearchResultsUseCompactTicketRowPresentation() throws {
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)
        let rowBlock = try sourceBlock(
            in: source,
            from: "private func showRows(",
            to: ".accessibilityIdentifier(LaughTrackViewTestID.showsSearchResultButton(show.id))"
        )

        #expect(rowBlock.contains("ShowRow("))
        #expect(rowBlock.contains("show.id == standoutShowID ? .compactTicketProminent : .compactTicket"))
        #expect(rowBlock.contains("AdaptiveSearchResults(spacing: theme.spacing.md)"))
        #expect(rowBlock.contains("context: ShowRowContext = .standalone"))
        #expect(rowBlock.contains("context: context"))
        #expect(source.contains("showRows(section.shows, standoutShowID: standoutShowID, context: .agenda)"))
        #expect(source.contains("showRows(result.items, standoutShowID: ShowsListStandout.resolveID(in: result.items))"))
    }

    @Test("show explorer exposes quick dates and consolidates location and secondary filters")
    func showExplorerKeepsPrimaryControlsCompact() throws {
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)
        let filters = try sourceBlock(
            in: source,
            from: "private struct ShowFiltersPanel: View",
            to: "private struct ShowResultsCalendarView: View"
        )

        #expect(!filters.contains("Start with what matters"))
        #expect(!filters.contains("shows-distance"))
        #expect(!filters.contains("shows-max-price"))
        #expect(filters.contains("ForEach(ShowHeaderDateChoice.allCases)"))
        #expect(filters.contains("model.applyDateShortcut(choice.rawValue)"))
        #expect(filters.contains("isFilterEditorPresented = true"))
        #expect(filters.contains("Edit location and radius"))
        #expect(ShowFormatOption.allCases.map(\.title) == ["Stand-up", "Improv", "Open mic"])
        #expect(source.contains("Comedian (optional)"))
        #expect(source.contains("Club (optional)"))
        #expect(source.range(of: "ShowFiltersPanel(")!.lowerBound < source.range(of: "Comedian (optional)")!.lowerBound)

        let dateSheet = try sourceBlock(
            in: source,
            from: "private struct ShowsDateRangeSheet: View",
            to: "private var mergedShowsByDate: [Date: Int]"
        )
        #expect(dateSheet.contains("todayTitle: \"Tonight\""))
        #expect(dateSheet.contains("title: \"This Weekend\""))
        #expect(dateSheet.contains("model.applyDateShortcut(\"This Weekend\")"))
        #expect(dateSheet.contains("model.sort = .earliest"))
    }

    @Test("additional filters include free and show formats but exclude legacy price buckets")
    func additionalFiltersIncludeShowFacets() throws {
        let availableSlugs = [
            "standup", "improv", "open_mic", "open mic", "free",
            "0-20", "20-50", "50-100", ">100", "late-night", "clean"
        ]

        let secondarySlugs = availableSlugs.filter(ShowFilterFacetTaxonomy.isSecondary(slug:))
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)
        let taxonomyUsageCount = source.components(
            separatedBy: "ShowFilterFacetTaxonomy.isSecondary(slug: $0.slug)"
        ).count - 1

        #expect(secondarySlugs == [
            "standup", "improv", "open_mic", "open mic", "free", "late-night", "clean"
        ])
        #expect(taxonomyUsageCount == 1)
    }

    @Test("show results default to a grouped agenda and offer density calendar")
    func showResultsOfferAgendaAndDensityCalendar() throws {
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)

        #expect(ShowResultsPresentation.allCases == [.agenda, .calendar])
        #expect(source.contains("Picker(\"Results view\", selection: $model.resultsPresentation)"))
        #expect(source.contains("ShowAgenda.sections(from: shows)"))
        #expect(source.contains("MonthCalendarView("))
        #expect(source.contains("DateRangeDensity.compute("))
    }

    @Test("external date facets synchronize the calendar without a reciprocal observer")
    func externalDateFacetsSynchronizeCalendarWithoutReciprocalObserver() throws {
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)
        let calendarBlock = try sourceBlock(
            in: source,
            from: "private struct ShowResultsCalendarView: View",
            to: "private var mergedShowsByDate: [Date: Int]"
        )

        #expect(calendarBlock.contains("selection: .single(calendarSelection)"))
        #expect(calendarBlock.contains(".onChange(of: model.dateRange)"))
        #expect(calendarBlock.contains(".id(MonthCalendarView.monthStart(for: selectedDate))"))
        #expect(!calendarBlock.contains(".onChange(of: selectedDate)"))
    }

    @Test("date sync maps external ranges and calendar taps in separate directions")
    func dateSyncMapsExternalRangesAndCalendarTaps() throws {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        let now = try #require(calendar.date(from: DateComponents(year: 2030, month: 4, day: 2, hour: 18)))
        let weekendStart = try #require(calendar.date(from: DateComponents(year: 2030, month: 4, day: 5, hour: 20)))
        let weekendEnd = try #require(calendar.date(from: DateComponents(year: 2030, month: 4, day: 7, hour: 23)))
        let tappedDate = try #require(calendar.date(from: DateComponents(year: 2030, month: 5, day: 9, hour: 21)))

        let externalSelection = ShowCalendarDateSync.selectedDate(
            for: DateRangeFilter(from: weekendStart, to: weekendEnd, isActive: true),
            now: now,
            calendar: calendar
        )
        let inactiveSelection = ShowCalendarDateSync.selectedDate(
            for: DateRangeFilter(from: weekendStart, to: weekendEnd, isActive: false),
            now: now,
            calendar: calendar
        )
        let tappedRange = ShowCalendarDateSync.exactDateRange(for: tappedDate, calendar: calendar)

        #expect(externalSelection == calendar.startOfDay(for: weekendStart))
        #expect(inactiveSelection == calendar.startOfDay(for: now))
        #expect(tappedRange.from == calendar.startOfDay(for: tappedDate))
        #expect(tappedRange.to == tappedRange.from)
        #expect(tappedRange.isActive)
    }

    @Test("agenda groups shows by day and sorts days and start times")
    func agendaGroupsAndSortsShows() throws {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        let dayOne = try #require(calendar.date(from: DateComponents(year: 2030, month: 4, day: 2)))
        let dayTwo = try #require(calendar.date(from: DateComponents(year: 2030, month: 4, day: 3)))
        let shows = [
            makeShow(id: 3, date: dayTwo.addingTimeInterval(72_000)),
            makeShow(id: 2, date: dayOne.addingTimeInterval(72_000)),
            makeShow(id: 1, date: dayOne.addingTimeInterval(64_800)),
        ]

        let sections = ShowAgenda.sections(from: shows, calendar: calendar)

        #expect(sections.map(\.day) == [dayOne, dayTwo])
        #expect(sections[0].shows.map(\.id) == [1, 2])
        #expect(sections[1].shows.map(\.id) == [3])
    }

    @Test("standout resolver picks the single highest positive popularity score")
    func standoutResolverPicksSingleHighestPositiveScore() {
        let shows = [
            makeShow(id: 1, popularityScore: 0.2),
            makeShow(id: 2, popularityScore: 0.9),
            makeShow(id: 3, popularityScore: 0.4),
        ]

        #expect(ShowsListStandout.resolveID(in: shows) == 2)
    }

    @Test("standout resolver returns nil when there is no clear positive winner")
    func standoutResolverReturnsNilWithoutClearPositiveWinner() {
        #expect(ShowsListStandout.resolveID(in: [
            makeShow(id: 1, popularityScore: nil),
            makeShow(id: 2, popularityScore: 0),
        ]) == nil)
        #expect(ShowsListStandout.resolveID(in: [
            makeShow(id: 1, popularityScore: 0.8),
            makeShow(id: 2, popularityScore: 0.8),
        ]) == nil)
    }

    private func showsListViewSourceURL(filePath: String = #filePath) throws -> URL {
        let testsURL = URL(fileURLWithPath: filePath)
        let iosRoot = testsURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        return iosRoot.appendingPathComponent("Sources/LaughTrackApp/Search/Views/ShowsListView.swift")
    }

    private func sourceBlock(in source: String, from start: String, to end: String) throws -> String {
        guard let startRange = source.range(of: start) else {
            throw SourceBlockError.missingStart(start)
        }
        guard let endRange = source[startRange.upperBound...].range(of: end) else {
            throw SourceBlockError.missingEnd(end)
        }
        return String(source[startRange.lowerBound..<endRange.upperBound])
    }

    private enum SourceBlockError: Error {
        case missingStart(String)
        case missingEnd(String)
    }

    private func makeShow(
        id: Int,
        date: Date = Date(timeIntervalSince1970: 1_710_000_000),
        popularityScore: Double? = nil
    ) -> Components.Schemas.Show {
        Components.Schemas.Show(
            id: id,
            clubId: 20,
            date: date,
            name: "Show \(id)",
            popularityScore: popularityScore,
            imageUrl: "https://example.com/show-\(id).jpg"
        )
    }
}


@Suite("Search agenda venue dates")
@MainActor
struct SearchAgendaTimezoneTests {
    @Test("Destination tickets and agenda agree across midnight and DST", arguments: [
        ("2026-08-17T04:00:00Z", "America/Los_Angeles", "America/New_York", 16),
        ("2026-08-17T07:30:00Z", "America/Los_Angeles", "America/New_York", 17),
        ("2026-03-08T04:30:00Z", "America/New_York", "Europe/London", 7),
        ("2026-03-08T07:30:00Z", "America/New_York", "Europe/London", 8),
        ("2026-11-01T05:30:00Z", "America/New_York", "America/Los_Angeles", 1),
        ("2026-11-01T06:30:00Z", "America/New_York", "America/Los_Angeles", 1),
        ("2026-08-17T00:30:00Z", "Asia/Tokyo", "America/Los_Angeles", 17)
    ])
    func venueDate(instant: String, venue: String, device: String, expectedDay: Int) throws {
        let calendar = try calendar(in: device)
        let show = try show(1, instant, venue)
        let section = try #require(ShowAgenda.sections(from: [show], calendar: calendar).first)
        let stack = ShowFormatting.dateStack(show.date, timezoneID: venue, localTimezone: calendar.timeZone)
        #expect(calendar.component(.day, from: section.day) == expectedDay)
        #expect(stack.day == String(expectedDay))
        #expect(stack.time.contains(try #require(TimeZone(identifier: venue)?.abbreviation(for: show.date))))
    }

    @Test("Mixed venues share a civil-date heading without splitting by midnight instant")
    func mixedVenues() throws {
        let calendar = try calendar(in: "Europe/London")
        let shows = try [
            show(1, "2026-08-17T02:00:00Z", "America/New_York"),
            show(2, "2026-08-17T06:30:00Z", "America/Los_Angeles"),
            show(3, "2026-08-17T07:30:00Z", "America/Los_Angeles")
        ]
        let sections = ShowAgenda.sections(from: shows.reversed(), calendar: calendar)
        #expect(sections.map { calendar.component(.day, from: $0.day) } == [16, 17])
        #expect(sections.map { $0.shows.map(\.id) } == [[1, 2], [3]])
        let selected = ShowCalendarDateSync.exactDateRange(for: sections[0].day, calendar: calendar)
        #expect(calendar.component(.day, from: selected.from) == 16)
        #expect(selected.to == selected.from)
    }

    @Test("Missing and invalid venue timezones fall back to the device day", arguments: [nil, "Invalid/Zone"] as [String?])
    func missingTimezone(zone: String?) throws {
        let calendar = try calendar(in: "America/Los_Angeles")
        let show = try show(1, "2026-08-17T04:00:00Z", zone)
        let section = try #require(ShowAgenda.sections(from: [show], calendar: calendar).first)
        #expect(calendar.component(.day, from: section.day) == 16)
        #expect(ShowFormatting.dateStack(show.date, timezoneID: zone, localTimezone: calendar.timeZone).day == "16")
    }

    @Test("Density civil dates remain on the selected day in any device zone", arguments: ["America/Los_Angeles", "Asia/Tokyo"])
    func densityCivilDate(device: String) throws {
        let calendar = try calendar(in: device)
        let map = DateRangeDensity.densityMap(from: ["2030-08-18": 2, "2030-08-19": 1], calendar: calendar)
        #expect(map.count == 2)
        #expect(map.first { calendar.component(.day, from: $0.key) == 18 }?.value == 2)
        #expect(map.first { calendar.component(.day, from: $0.key) == 19 }?.value == 1)
    }

    @Test("Search and calendar requests opt into the same venue date convention")
    func requestDateConvention() async throws {
        let transport = StubClientTransport { _, _, _, operation in
            let body = operation == "getShowsDensity"
                ? #"{"2030-08-18":2}"#
                : #"{"data":[],"total":0,"filters":[],"zipCapTriggered":false}"#
            return (HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]), HTTPBody(body))
        }
        let client = Client(serverURL: URL(string: "https://example.com")!, configuration: .laughTrack, transport: transport)
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "agenda-request")
        let model = ShowsListModel(nearbyLocationController: LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store))
        let calendar = Calendar.current
        let day = try #require(calendar.date(from: DateComponents(year: 2030, month: 8, day: 18)))
        model.dateRange = ShowCalendarDateSync.exactDateRange(for: day)
        await model.reload(apiClient: client)
        let density = await DateRangeDensity.compute(preference: nil, clubId: 20, fromDate: day, toDate: day, now: day, apiClient: client)
        #expect(density?[day] == 2)
        #expect(transport.capturedRequests.count == 2)
        for request in transport.capturedRequests {
            let components = try #require(URLComponents(string: "https://example.com" + (request.path ?? "")))
            let params = Dictionary(uniqueKeysWithValues: (components.queryItems ?? []).map { ($0.name, $0.value ?? "") })
            #expect(params["from"] == "2030-08-18")
            #expect(params["to"] == "2030-08-18")
            #expect(params["dateBasis"] == "venue")
        }
        #expect(model.requestKey.cacheKey.contains("dateBasis=venue"))
        #expect(model.requestKey.cacheKey.contains(TimeZone.autoupdatingCurrent.identifier))
    }

    #if canImport(UIKit)
    @Test("Capture Search agenda with Los Angeles shows either side of midnight")
    func destinationAgendaCapture() async throws {
        // Record the device zone for visual-audit provenance without making the
        // regression suite depend on a developer machine's global timezone.
        print("Timezone agenda capture device zone: \(TimeZone.current.identifier)")
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "agenda-capture")
        let model = ShowsListModel(
            nearbyLocationController: LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store),
            initialUseDateRange: false, startsWithNearbyLocation: false
        )
        let shows = try [
            show(1, "2030-08-19T06:30:00Z", "America/Los_Angeles"),
            show(2, "2030-08-19T07:30:00Z", "America/Los_Angeles")
        ]
        await model.reload(query: model.requestKey) { _, _ in .success(.init(items: shows, total: shows.count)) }
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "agenda-capture")
        let host = HostedView(
            ScrollView {
                ShowsListView(apiClient: LaughTrackHostedViewTestSupport.makeClient(), model: model, displaysSearchFields: false, isActive: false)
                    .padding(16)
            }
            .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .environmentObject(TypedNavigationCoordinator<AppRoute>())
            .preferredColorScheme(.dark)
        )
        await host.settle(iterations: 4)
        for position in ["top", "scrolled"] {
            if position == "scrolled" { host.scrollDown(pages: 1); await host.settle(iterations: 2) }
            let image = try host.snapshot()
            let data = try #require(image.pngData())
            let name = "task4006-destination-agenda-\(position).png"
            #if compiler(>=6.2)
            Attachment.record(Array(data), named: name)
            #endif
            let artifact = FileManager.default.temporaryDirectory.appendingPathComponent(name)
            try data.write(to: artifact)
            print("Timezone agenda capture: \(artifact.path)")
        }
    }
    #endif

    private func calendar(in zone: String) throws -> Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = try #require(TimeZone(identifier: zone))
        return calendar
    }

    private func show(_ id: Int, _ instant: String, _ zone: String?) throws -> Components.Schemas.Show {
        Components.Schemas.Show(
            id: id, clubId: 20,
            date: try #require(ISO8601DateFormatter().date(from: instant)),
            name: "Timezone show \(id)", imageUrl: "https://example.com/show.jpg", timezone: zone
        )
    }
}


#if canImport(UIKit)
import UIKit
import Vision

@Suite("Shows header visual capture", .serialized)
@MainActor
struct ShowsHeaderVisualCaptureTests {
    @Test("capture the live Shows layout at standard and accessibility sizes")
    func captureHeader() async throws {
        for size in [DynamicTypeSize.large, .accessibility5] {
            let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "header-capture")
            let model = ShowsListModel(nearbyLocationController: LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store), initialUseDateRange: false, startsWithNearbyLocation: false)
            model.zipCodeDraft = "10012"
            #expect(model.applyManualZip())
            let shows = (1...6).map { id in
                Components.Schemas.Show(id: id, clubId: 20, clubName: "The Stand", date: Date(timeIntervalSince1970: 1_913_400_000 + Double(id) * 1800), name: "Comedy showcase \(id)", lineup: [], imageUrl: "", timezone: "America/New_York")
            }
            await model.reload(query: model.requestKey) { _, _ in .success(.init(items: shows, total: shows.count)) }
            let host = HostedView(
                ScrollView {
                    ShowsListView(apiClient: LaughTrackHostedViewTestSupport.makeClient(), model: model, isActive: false)
                        .padding(.horizontal, 20).padding(.top, 8)
                }
                .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.dynamicTypeSize, size)
                .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "header-capture"))
                .environmentObject(TypedNavigationCoordinator<AppRoute>())
                .preferredColorScheme(.dark), freshWindow: true
            )
            await host.settle(iterations: 3)
            let data = try #require(try host.snapshot().pngData())
            let device = UIDevice.current.userInterfaceIdiom == .pad ? "ipad" : "phone"
            let textSize = size.isAccessibilitySize ? "AX5" : "standard"
            let path = FileManager.default.temporaryDirectory.appendingPathComponent("task4001-\(device)-\(textSize).png")
            try data.write(to: path)
            print("Shows header capture: \(path.path)")
            #if compiler(>=6.2)
            Attachment.record(Array(data), named: path.lastPathComponent)
            #endif
        }
    }
}

@Suite("Search refresh presentation", .serialized)
@MainActor
struct SearchRefreshPresentationTests {
    @Test("actual Shows search retains rows during refresh and recovers after a failed request")
    func showsRefreshFailureAndRecovery() async throws {
        let model = makeModel("refresh-flow")
        let refreshed = [show(20)]
        let data = try APIMockEncoder.make().encode(Components.Schemas.ShowSearchResponse(
            data: refreshed, total: refreshed.count, filters: [], zipCapTriggered: false
        ))
        let transport = StubClientTransport { _, _, _, operationID in
            #expect(operationID == "searchShows")
            return (HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]), HTTPBody(data))
        }
        let client = Client(serverURL: URL(string: "https://example.com")!, configuration: .laughTrack, transport: transport)
        let host = makeHost(model, client: client)
        await host.settle(iterations: 3)
        if case .idle = model.phase {} else { Issue.record("Inactive hosted search should initially be idle") }
        #expect(!(try capture(host, name: "initial")).contains("showing 2 of 2"))
        await model.reload(query: model.requestKey) { _, _ in .success(.init(items: [show(1), show(2)], total: 2)) }
        await host.settle(iterations: 3)
        #expect(try capture(host, name: "loaded").contains("showing 2 of 2"))
        #expect(model.currentItems.map(\.id) == [1, 2])

        model.comedianSearchText = "Ray"
        let gate = SearchPresentationResponseGate()
        let refresh = Task { await model.reload(query: model.requestKey) { _, _ in await gate.fetch() } }
        try await waitUntil { gate.isWaiting }
        await host.settle(iterations: 3)
        let updatingText = try capture(host, name: "updating")
        #expect(updatingText.contains("updating results"))
        #expect(updatingText.contains("previous results shown"))
        #expect(!updatingText.contains("showing 2 of 2"))
        #expect(model.currentItems.map(\.id) == [1, 2])
        gate.resolve(.failure(.network("Offline")))
        await refresh.value
        await host.settle(iterations: 3)
        let offlineText = try capture(host, name: "offline")
        #expect(offlineText.contains("update results"))
        #expect(offlineText.contains("retry"))
        #expect(model.currentItems.map(\.id) == [1, 2])
        await model.reload(apiClient: client)
        try await waitUntil { model.resultsState(for: model.requestKey).isConfirmed }
        await host.settle(iterations: 3)
        #expect(transport.capturedRequests.count == 1)
        #expect(try capture(host, name: "recovered").contains("showing 1 of 1"))
        #expect(model.currentItems.map(\.id) == [20])
    }

    @Test("previous empty results stay honest while a new query updates")
    func previousEmptyResultsStayHonest() async throws {
        let model = makeModel("empty-refresh")
        model.comedianSearchText = "Missing"
        await model.reload(query: model.requestKey) { _, _ in .success(.init(items: [], total: 0)) }
        let host = makeHost(model)
        await host.settle(iterations: 3)
        #expect(try capture(host, name: "previous-empty").contains("no matches"))
        model.comedianSearchText = "Ray"
        let gate = SearchPresentationResponseGate()
        let refresh = Task { await model.reload(query: model.requestKey) { _, _ in await gate.fetch() } }
        try await waitUntil { gate.isWaiting }
        await host.settle(iterations: 3)
        let updatingText = try capture(host, name: "previous-empty-updating")
        #expect(updatingText.contains("updating results"))
        #expect(updatingText.contains("no previous results"))
        #expect(!updatingText.contains("no matches"))
        gate.resolve(.success(.init(items: [show(20)], total: 1)))
        await refresh.value
        await host.settle(iterations: 3)
        #expect(try capture(host, name: "previous-empty-settled").contains("showing 1 of 1"))
        #expect(model.currentItems.map(\.id) == [20])
    }

    @Test("refresh preserves the actual scroll offset and content height")
    func refreshKeepsScrollPosition() async throws {
        let model = makeModel("scroll-refresh")
        let shows = (1...12).map(show)
        await model.reload(query: model.requestKey) { _, _ in .success(.init(items: shows, total: shows.count)) }
        let host = makeHost(model)
        await host.settle(iterations: 3)
        _ = try host.snapshot()
        host.scrollDown(pages: 0.5)
        await host.settle(iterations: 2)
        let originalMetrics = try #require(host.scrollMetrics())
        let offset = originalMetrics.offset
        #expect(offset > 0)
        let contentHeight = originalMetrics.contentHeight
        // Sort changes affect results without inserting a new active-filter chip.
        model.sort = .latest
        let gate = SearchPresentationResponseGate()
        let refresh = Task { await model.reload(query: model.requestKey) { _, _ in await gate.fetch() } }
        try await waitUntil { gate.isWaiting }
        await host.settle(iterations: 3)
        _ = try capture(host, name: "scrolled-updating")
        let updatingMetrics = try #require(host.scrollMetrics())
        #expect(abs(updatingMetrics.offset - offset) < 1)
        #expect(abs(updatingMetrics.contentHeight - contentHeight) < 1)
        gate.resolve(.success(.init(items: shows, total: shows.count)))
        await refresh.value
        await host.settle(iterations: 3)
        #expect(abs(try #require(host.scrollMetrics()).offset - offset) < 1)
    }

    private func makeModel(_ name: String) -> ShowsListModel {
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: name)
        return ShowsListModel(
            nearbyLocationController: LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store),
            initialUseDateRange: false, startsWithNearbyLocation: false
        )
    }

    private func makeHost(_ model: ShowsListModel, client: Client? = nil) -> HostedView {
        HostedView(
            ScrollView {
                ShowsListView(apiClient: client ?? LaughTrackHostedViewTestSupport.makeClient(), model: model,
                              displaysSearchFields: false, isActive: false)
                    .padding(16)
            }
            .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "refresh-host"))
            .environmentObject(TypedNavigationCoordinator<AppRoute>())
            .preferredColorScheme(.dark)
        )
    }

    private func show(_ id: Int) -> Components.Schemas.Show {
        .init(id: id, clubId: 20, clubName: "The Stand",
              date: Date(timeIntervalSince1970: 1_913_400_000 + Double(id) * 1800),
              tickets: [.init(price: 25, purchaseUrl: "https://example.com/tickets", soldOut: false, _type: "General admission")],
              name: "Comedy showcase \(id)", lineup: [], imageUrl: "", timezone: "America/New_York")
    }

    /// Inspect rendered pixels because this simulator does not publish the
    /// hosted SwiftUI accessibility tree. Persist each image before assertions.
    private func capture(_ host: HostedView, name: String) throws -> String {
        let image = try host.snapshot()
        let data = try #require(image.pngData())
        let reduceMotion = UIAccessibility.isReduceMotionEnabled
        let suffix = reduceMotion ? "-reduce-motion" : ""
        let filename = "task4007-\(name)\(suffix).png"
        print("Search refresh system Reduce Motion: \(reduceMotion)")
        #if compiler(>=6.2)
        Attachment.record(Array(data), named: filename)
        #endif
        let path = FileManager.default.temporaryDirectory.appendingPathComponent(filename)
        try data.write(to: path)
        print("Search refresh capture: \(path.path)")
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = ["en-US"]
        let handler = VNImageRequestHandler(cgImage: try #require(image.cgImage))
        try handler.perform([request])
        let text = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
            .joined(separator: " ").lowercased()
        print("Search refresh OCR \(name): \(text)")
        return text
    }

    private func waitUntil(_ condition: () -> Bool) async throws {
        let deadline = Date().addingTimeInterval(4)
        while !condition(), Date() < deadline { try await Task.sleep(for: .milliseconds(5)) }
        try #require(condition(), "Timed out waiting for hosted Search request")
    }
}

@MainActor
private final class SearchPresentationResponseGate {
    typealias Response = Result<DiscoverySearchResponse<Components.Schemas.Show>, LoadFailure>
    private var continuation: CheckedContinuation<Response, Never>?
    var isWaiting: Bool { continuation != nil }
    func fetch() async -> Response {
        await withCheckedContinuation { continuation = $0 }
    }
    func resolve(_ response: Response) {
        continuation?.resume(returning: response)
        continuation = nil
    }
}
#endif

#if canImport(UIKit)
@Suite("Search empty visual capture", .serialized)
@MainActor
struct SearchEmptyVisualCaptureTests {
    @Test("capture confirmed query misses in live Search views")
    func captureEmptyScreens() async throws {
        for size in [DynamicTypeSize.large, .accessibility5] {
            for category in ["comedians", "clubs", "shows"] {
                let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "empty-capture")
                let location = container.resolve(NearbyLocationController.self)
                let comedians = ComediansDiscoveryModel()
                comedians.searchText = "Ray Devito"
                let clubs = ClubsDiscoveryModel(nearbyLocationController: location)
                clubs.searchText = "Comedy Cellar"
                let shows = ShowsListModel(nearbyLocationController: location, initialUseDateRange: false, startsWithNearbyLocation: false)
                shows.comedianSearchText = "Ray Devito"
                await comedians.reload(query: comedians.requestKey) { _, _ in .success(.init(items: [], total: 0)) }
                await clubs.reload(query: clubs.requestKey) { _, _ in .success(.init(items: [], total: 0)) }
                await shows.reload(query: shows.requestKey) { _, _ in .success(.init(items: [], total: 0)) }
                let client = LaughTrackHostedViewTestSupport.makeClient()
                let host = HostedView(
                    ScrollView {
                        VStack(alignment: .leading, spacing: 16) {
                            Text("Search").font(.largeTitle.bold())
                            if category == "comedians" {
                                ComediansDiscoveryView(apiClient: client, model: comedians, isActive: false)
                            } else if category == "clubs" {
                                ClubsDiscoveryView(apiClient: client, model: clubs, isActive: false)
                            } else {
                                ShowsListView(apiClient: client, model: shows, isActive: false)
                            }
                        }.padding(20)
                    }
                    .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
                    .environment(\.appTheme, LaughTrackTheme())
                    .environment(\.dynamicTypeSize, size)
                    .environment(\.serviceContainer, container)
                    .environmentObject(TypedNavigationCoordinator<AppRoute>())
                    .environmentObject(ComedianFavoriteStore())
                    .preferredColorScheme(.dark), freshWindow: true
                )
                await host.settle(iterations: 5)
                let data = try #require(try host.snapshot().pngData())
                let textSize = size.isAccessibilitySize ? "AX5" : "standard"
                let path = FileManager.default.temporaryDirectory.appendingPathComponent("task4010-\(category)-\(textSize).png")
                try data.write(to: path)
                print("Search empty capture: \(path.path)")
                #if compiler(>=6.2)
                Attachment.record(Array(data), named: path.lastPathComponent)
                #endif
                if size.isAccessibilitySize,
                   let window = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).flatMap(\.windows).first(where: \.isKeyWindow),
                   let scroll = firstScrollView(in: window) {
                    scroll.setContentOffset(CGPoint(x: 0, y: max(0, scroll.contentSize.height - scroll.bounds.height)), animated: false)
                    await host.settle(iterations: 5)
                    let scrolled = try #require(try host.snapshot().pngData())
                    let bottom = path.deletingPathExtension().appendingPathExtension("bottom.png")
                    try scrolled.write(to: bottom)
                    print("Search empty capture: \(bottom.path)")
                    #if compiler(>=6.2)
                    Attachment.record(Array(scrolled), named: bottom.lastPathComponent)
                    #endif
                }
            }
        }
    }
    private func firstScrollView(in view: UIView) -> UIScrollView? {
        if let scroll = view as? UIScrollView, scroll.contentSize.height > scroll.bounds.height { return scroll }
        return view.subviews.lazy.compactMap { firstScrollView(in: $0) }.first
    }

}
#endif


@Suite("Detail content hierarchy")
@MainActor
struct DetailContentHierarchyTests {
    @Test("compact artwork reduces occupied space across each marquee type")
    func compactArtwork() {
        let phone = MarqueeHeroLayout(isCompact: true)
        let regular = MarqueeHeroLayout(isCompact: false)
        #expect(phone.posterImageSize >= 100)
        #expect(regular.posterImageSize - phone.posterImageSize >= 80)
        #expect(regular.comedianFrameSize.height - phone.comedianFrameSize.height >= 100)
        #expect(regular.podcastStageSize.height - phone.podcastStageSize.height >= 50)
        #expect(phone.comedianPhotoSize < phone.comedianFrameSize.width)
        #expect(phone.podcastCoverSize < phone.podcastStageSize.width)
        #expect(phone.contentSpacing < regular.contentSpacing)
    }

    @Test("regular-width artwork retains its established dimensions")
    func regularArtwork() {
        let regular = MarqueeHeroLayout(isCompact: false)
        #expect(regular.posterImageSize == 196)
        #expect(regular.comedianPhotoSize == 208)
        #expect(regular.comedianFrameSize == CGSize(width: 244, height: 278))
        #expect(regular.podcastCoverSize == 150)
        #expect(regular.podcastStageSize == CGSize(width: 224, height: 210))
        #expect(DetailCatalogComposition.resolve(horizontalSizeClass: .regular) == .regularColumns)
        #expect(DetailCatalogComposition.resolve(horizontalSizeClass: .compact) == .compactStack)
    }

    @Test("attendance actions remain direct and website actions remain secondary")
    func actionRoles() {
        let club = Components.Schemas.ClubDetail(id: 201, name: "Venue", imageUrl: "", heroImageUrl: "", website: "https://example.com", address: "117 MacDougal St")
        let actions = ClubDetailHeroPresentation.actions(for: club)
        #expect(actions.first { $0.title == "Directions" }?.role == .attendance)
        #expect(actions.first { $0.title == "Website" }?.role == .secondary)
        #expect(DetailHeroAction(title: "RSS", systemImage: "dot.radiowaves.left.and.right", url: URL(string: "https://example.com/feed")).role == .secondary)
    }

    @Test("only entity-scoped lists receive the Upcoming shows heading")
    func scopedHeading() {
        #expect(ShowsListChromeVisibility(compactMode: true).sectionTitle == "Upcoming shows")
        #expect(ShowsListChromeVisibility(compactMode: false).sectionTitle == nil)
    }
}
