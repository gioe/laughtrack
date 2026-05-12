#if canImport(UIKit)
import Foundation
import Testing
import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("Month calendar view")
struct MonthCalendarViewTests {
    @Test("range selection first tap starts a new range")
    func rangeSelectionFirstTapStartsNewRange() {
        let calendar = makeCalendar(firstWeekday: 1)
        let previousStart = date(2026, 5, 8, calendar: calendar)
        let previousEnd = date(2026, 5, 12, calendar: calendar)
        let tapped = date(2026, 5, 14, hour: 18, calendar: calendar)

        let result = MonthCalendarView.rangeSelection(
            afterTap: tapped,
            start: previousStart,
            end: previousEnd,
            awaitingEnd: false,
            calendar: calendar
        )

        #expect(result.start == date(2026, 5, 14, calendar: calendar))
        #expect(result.end == date(2026, 5, 14, calendar: calendar))
        #expect(result.awaitingEnd)
    }

    @Test("range selection later second tap extends the end")
    func rangeSelectionLaterSecondTapExtendsRange() {
        let calendar = makeCalendar(firstWeekday: 1)
        let start = date(2026, 5, 8, calendar: calendar)
        let tapped = date(2026, 5, 12, hour: 22, calendar: calendar)

        let result = MonthCalendarView.rangeSelection(
            afterTap: tapped,
            start: start,
            end: start,
            awaitingEnd: true,
            calendar: calendar
        )

        #expect(result.start == start)
        #expect(result.end == date(2026, 5, 12, calendar: calendar))
        #expect(!result.awaitingEnd)
    }

    @Test("range selection earlier second tap swaps endpoints")
    func rangeSelectionEarlierSecondTapSwapsRange() {
        let calendar = makeCalendar(firstWeekday: 1)
        let start = date(2026, 5, 8, calendar: calendar)
        let tapped = date(2026, 5, 3, hour: 9, calendar: calendar)

        let result = MonthCalendarView.rangeSelection(
            afterTap: tapped,
            start: start,
            end: start,
            awaitingEnd: true,
            calendar: calendar
        )

        #expect(result.start == date(2026, 5, 3, calendar: calendar))
        #expect(result.end == start)
        #expect(!result.awaitingEnd)
    }

    @Test("leading nils respect Sunday-start and non-Sunday-start months under Monday-first calendars")
    func leadingNilsRespectMondayFirstCalendar() {
        let calendar = makeCalendar(firstWeekday: 2)

        let sundayStartRows = MonthCalendarView.rows(
            for: date(2024, 9, 15, calendar: calendar),
            calendar: calendar
        )
        let tuesdayStartRows = MonthCalendarView.rows(
            for: date(2024, 10, 15, calendar: calendar),
            calendar: calendar
        )

        #expect(sundayStartRows[0].prefix { $0 == nil }.count == 6)
        #expect(tuesdayStartRows[0].prefix { $0 == nil }.count == 1)
    }

    @Test("leading nils are empty for Sunday-start months under Sunday-first calendars")
    func leadingNilsRespectSundayFirstCalendar() {
        let calendar = makeCalendar(firstWeekday: 1)

        let rows = MonthCalendarView.rows(
            for: date(2024, 9, 15, calendar: calendar),
            calendar: calendar
        )

        #expect(rows[0].prefix { $0 == nil }.count == 0)
    }

    @Test("weekday symbols rotate for Sunday-first and Monday-first calendars")
    func weekdaySymbolsRotateByFirstWeekday() {
        let sundayFirst = MonthCalendarView.weekdaySymbols(for: makeCalendar(firstWeekday: 1))
        let mondayFirst = MonthCalendarView.weekdaySymbols(for: makeCalendar(firstWeekday: 2))

        #expect(sundayFirst.first == "S")
        #expect(sundayFirst.dropFirst().first == "M")
        #expect(mondayFirst.first == "M")
        #expect(mondayFirst.last == "S")
    }

    @Test("minimum month gating only disables months strictly before the minimum")
    func minimumMonthGatingIsStrict() {
        let calendar = makeCalendar(firstWeekday: 1)
        let minimum = date(2026, 5, 18, calendar: calendar)

        #expect(!MonthCalendarView.isMonth(date(2026, 5, 1, calendar: calendar), beforeMinimum: minimum, calendar: calendar))
        #expect(!MonthCalendarView.isMonth(date(2026, 6, 1, calendar: calendar), beforeMinimum: minimum, calendar: calendar))
        #expect(MonthCalendarView.isMonth(date(2026, 4, 30, calendar: calendar), beforeMinimum: minimum, calendar: calendar))
    }

    @Test("nil minimum date disables day and month gating")
    func nilMinimumDateDisablesGating() {
        let calendar = makeCalendar(firstWeekday: 1)

        #expect(!MonthCalendarView.isDate(date(2026, 1, 10, calendar: calendar), beforeMinimum: nil, calendar: calendar))
        #expect(!MonthCalendarView.isMonth(date(2026, 1, 1, calendar: calendar), beforeMinimum: nil, calendar: calendar))
    }

    @Test("monthStartForJump rejects months strictly before the minimum month")
    func monthStartForJumpRejectsMonthsBeforeMinimum() {
        let calendar = makeCalendar(firstWeekday: 1)
        let minimum = date(2026, 5, 18, calendar: calendar)

        // April 2026 is the month before the minimum's month — must reject.
        let aprilJump = MonthCalendarView.monthStartForJump(
            year: 2026,
            monthIndex: 3,
            minimumDate: minimum,
            calendar: calendar
        )
        #expect(aprilJump == nil)

        // May 2026 contains the minimum date — must accept and return May 1.
        let mayJump = MonthCalendarView.monthStartForJump(
            year: 2026,
            monthIndex: 4,
            minimumDate: minimum,
            calendar: calendar
        )
        #expect(mayJump == date(2026, 5, 1, calendar: calendar))

        // June 2026 is after the minimum's month — must accept.
        let juneJump = MonthCalendarView.monthStartForJump(
            year: 2026,
            monthIndex: 5,
            minimumDate: minimum,
            calendar: calendar
        )
        #expect(juneJump == date(2026, 6, 1, calendar: calendar))

        // Nil minimum disables gating — any year/month resolves.
        let unboundedJump = MonthCalendarView.monthStartForJump(
            year: 2020,
            monthIndex: 0,
            minimumDate: nil,
            calendar: calendar
        )
        #expect(unboundedJump == date(2020, 1, 1, calendar: calendar))
    }

    @Test("comedian detail show counts are bucketed by current calendar start of day")
    func comedianShowsByDateBucketsByStartOfDay() {
        let calendar = Calendar.current
        let firstShow = currentCalendarDate(2026, 5, 8, hour: 10)
        let secondShow = currentCalendarDate(2026, 5, 8, hour: 22)
        let nextDayShow = currentCalendarDate(2026, 5, 9, hour: 1)

        let counts = ComedianDetailView.showsByDate([
            upcomingRun(clubID: 1, shows: [
                show(id: 1, date: firstShow),
                show(id: 2, date: secondShow),
            ]),
            upcomingRun(clubID: 2, shows: [
                show(id: 3, date: nextDayShow),
            ]),
        ])

        #expect(counts[calendar.startOfDay(for: firstShow)] == 2)
        #expect(counts[calendar.startOfDay(for: nextDayShow)] == 1)
    }

    private func makeCalendar(firstWeekday: Int) -> Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.locale = Locale(identifier: "en_US_POSIX")
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        calendar.firstWeekday = firstWeekday
        return calendar
    }

    private func date(
        _ year: Int,
        _ month: Int,
        _ day: Int,
        hour: Int = 0,
        calendar: Calendar
    ) -> Date {
        calendar.date(from: DateComponents(year: year, month: month, day: day, hour: hour))!
    }

    private func currentCalendarDate(_ year: Int, _ month: Int, _ day: Int, hour: Int) -> Date {
        Calendar.current.date(from: DateComponents(year: year, month: month, day: day, hour: hour))!
    }

    private func upcomingRun(
        clubID: Int,
        shows: [Components.Schemas.Show]
    ) -> Components.Schemas.UpcomingRun {
        .init(
            clubID: clubID,
            clubName: "Club \(clubID)",
            clubImageUrl: "https://example.com/club-\(clubID).png",
            shows: shows
        )
    }

    private func show(id: Int, date: Date) -> Components.Schemas.Show {
        .init(
            id: id,
            clubID: 100 + id,
            clubName: "Comedy Club",
            date: date,
            name: "Late show",
            imageUrl: "https://example.com/show-\(id).png"
        )
    }
}
#endif
