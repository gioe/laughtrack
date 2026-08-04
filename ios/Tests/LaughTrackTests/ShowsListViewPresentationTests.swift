import Foundation
import Testing
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

    @Test("show explorer exposes primary facets before optional entity search")
    func showExplorerExposesPrimaryFacetsFirst() throws {
        let source = try String(contentsOf: showsListViewSourceURL(), encoding: .utf8)
        let filters = try sourceBlock(
            in: source,
            from: "private struct ShowFiltersPanel: View",
            to: "private struct ShowResultsCalendarView: View"
        )

        for label in ["Tonight", "This Weekend", "Location", "Max price", "Free"] {
            #expect(filters.contains(label), "Missing directly discoverable facet: \(label)")
        }
        #expect(filters.contains("id: \"shows-distance\""))
        #expect(filters.contains("systemImage: \"calendar\""))
        #expect(ShowFormatOption.allCases.map(\.title) == ["Stand-up", "Improv", "Open mic"])
        #expect(source.contains("Comedian (optional)"))
        #expect(source.contains("Club (optional)"))
        #expect(source.range(of: "ShowFiltersPanel(")!.lowerBound < source.range(of: "Comedian (optional)")!.lowerBound)
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
