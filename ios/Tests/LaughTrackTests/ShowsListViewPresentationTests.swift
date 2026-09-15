import Foundation
import Testing
import SwiftUI
import HTTPTypes
import OpenAPIRuntime
import LaughTrackBridge
import LaughTrackCore
import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("Shows list view presentation")
struct ShowsListViewPresentationTests {
    @Test("compact pinned lists label date search without an eyebrow")
    func compactPinnedListsUseClearDateSearchHeading() throws {
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)

        #expect(source.contains("LaughTrackSectionHeader(title: \"Search dates\")"))
        #expect(!source.contains("LaughTrackSectionHeader(eyebrow: \"Calendar\""))
        #expect(source.contains("if compactMode, pageCount > 1"))
        #expect(source.contains("if !compactMode {\n                                SearchResultsSummary"))
        #expect(source.contains("LaughTrackPagedControls("))
        #expect(source.contains("if !compactMode, result.canLoadMore"))
        #expect(source.contains("await model.loadPage("))
    }

    @Test("show search results use compact ticket row presentation")
    func showSearchResultsUseCompactTicketRowPresentation() throws {
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)
        let rowBlock = try sourceBlock(
            in: source,
            from: "private func showRows(_ shows: [Components.Schemas.Show], standoutShowID: Int?)",
            to: ".accessibilityIdentifier(LaughTrackViewTestID.showsSearchResultButton(show.id))"
        )

        #expect(rowBlock.contains("ShowRow("))
        #expect(rowBlock.contains("show.id == standoutShowID ? .compactTicketProminent : .compactTicket"))
        #expect(rowBlock.contains("AdaptiveSearchResults(spacing: theme.spacing.md)"))
    }

    @Test("show explorer keeps date presets inside its single date sheet")
    func showExplorerKeepsFormatFacetsInAdditionalFilters() throws {
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)
        let filters = try sourceBlock(
            in: source,
            from: "private struct ShowFiltersPanel: View",
            to: "private struct ShowResultsCalendarView: View"
        )

        for label in ["Location", "Max price"] {
            #expect(filters.contains(label), "Missing directly discoverable facet: \(label)")
        }
        #expect(!filters.contains("title: \"Tonight\""))
        #expect(!filters.contains("title: \"This Weekend\""))
        #expect(filters.components(separatedBy: "isDateEditorPresented = true").count - 1 == 1)
        #expect(!filters.contains("title: \"Free\""))
        #expect(!filters.contains("title: ShowFormatOption.openMic.title"))
        #expect(!filters.contains("ForEach(ShowFormatOption.allCases"))
        #expect(filters.contains("id: \"shows-distance\""))
        #expect(filters.contains("systemImage: \"calendar\""))
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
        #expect(taxonomyUsageCount == 2)
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
            Attachment.record(Array(data), named: name)
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
