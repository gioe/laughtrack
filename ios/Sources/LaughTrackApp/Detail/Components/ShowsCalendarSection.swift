import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge

struct ShowsCalendarSection: View {
    @Environment(\.appTheme) private var theme

    let shows: [Components.Schemas.Show]
    let onSelectShow: (Int) -> Void
    @Binding var selectedDates: Set<Date>
    var jumpToDate: Binding<Date>? = nil
    var isRefreshing: Bool = false
    var isNearMe: ((Components.Schemas.Show) -> Bool)? = nil
    var thumbnailImageURL: ((Components.Schemas.Show) -> String?)? = nil

    @State private var isDatePickerPresented = false

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.md) {
            if jumpToDate != nil {
                headerControls
            }
            ShowsCalendarWeekStrip(
                dateRange: dateRange,
                showsByDate: showsByDate,
                selectedDates: $selectedDates
            )

            VStack(alignment: .leading, spacing: theme.spacing.md) {
                if filteredGroupedShows.isEmpty {
                    EmptyCard(message: emptyMessage)
                } else {
                    ForEach(filteredGroupedShows, id: \.date) { group in
                        ShowsCalendarDaySection(
                            date: group.date,
                            shows: group.shows,
                            onSelectShow: onSelectShow,
                            isNearMe: isNearMe,
                            thumbnailImageURL: thumbnailImageURL
                        )
                        .id(ShowsCalendarSection.dayKey(group.date))
                    }
                }
            }
        }
        .onChange(of: jumpToDate?.wrappedValue) { _ in
            // Clear chip selection when the user jumps weeks — previously-selected
            // dates may no longer be in the visible strip.
            selectedDates.removeAll()
        }
    }

    private var emptyMessage: String {
        if !selectedDates.isEmpty {
            return "No shows on the selected dates."
        }
        return "No shows scheduled this week."
    }

    private var filteredGroupedShows: [(date: Date, shows: [Components.Schemas.Show])] {
        // Clip the list to the visible week so it paginates with the strip.
        let weekDates = Set(dateRange.map { calendar.startOfDay(for: $0) })
        let inWeek = groupedShows.filter { weekDates.contains($0.date) }

        guard !selectedDates.isEmpty else { return inWeek }
        let normalized = Set(selectedDates.map { calendar.startOfDay(for: $0) })
        return inWeek.filter { normalized.contains($0.date) }
    }

    static func dayKey(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }

    @ViewBuilder
    private var headerControls: some View {
        if let jumpToDate {
            HStack(spacing: 8) {
                jumpToDatePill(binding: jumpToDate)
                if isRefreshing {
                    ProgressView()
                        .controlSize(.small)
                        .tint(theme.laughTrackTokens.colors.textSecondary)
                }
                Spacer(minLength: 0)
                weekStepButton(systemImage: "chevron.left", direction: -1, binding: jumpToDate)
                weekStepButton(systemImage: "chevron.right", direction: 1, binding: jumpToDate)
            }
            .disabled(isRefreshing)
        }
    }

    private func weekStepButton(systemImage: String, direction: Int, binding: Binding<Date>) -> some View {
        let calendar = Calendar.current
        let proposed = calendar.date(byAdding: .day, value: direction * 7, to: binding.wrappedValue) ?? binding.wrappedValue
        let today = calendar.startOfDay(for: Date())
        let clamped = max(proposed, today)
        let isDisabled = direction < 0 && calendar.isDate(binding.wrappedValue, inSameDayAs: today)

        return Button {
            binding.wrappedValue = clamped
        } label: {
            Image(systemName: systemImage)
                .font(.system(size: 13, weight: .bold))
                .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                .frame(width: 34, height: 34)
                .background(Circle().fill(theme.laughTrackTokens.colors.surfaceElevated))
                .overlay(Circle().stroke(theme.laughTrackTokens.colors.borderSubtle, lineWidth: 1))
        }
        .buttonStyle(.plain)
        .disabled(isDisabled)
        .opacity(isDisabled ? 0.4 : 1)
        .accessibilityLabel(direction < 0 ? "Previous week" : "Next week")
    }

    @ViewBuilder
    private func jumpToDatePill(binding: Binding<Date>) -> some View {
        Button {
            isDatePickerPresented = true
        } label: {
            HStack(spacing: 6) {
                Image(systemName: "calendar")
                    .font(.system(size: 13, weight: .semibold))
                Text(jumpPillLabel(binding.wrappedValue))
                    .font(.system(size: 14, weight: .semibold))
                Image(systemName: "chevron.down")
                    .font(.system(size: 11, weight: .semibold))
            }
            .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(
                Capsule().fill(theme.laughTrackTokens.colors.surfaceElevated)
            )
            .overlay(
                Capsule().stroke(theme.laughTrackTokens.colors.borderSubtle, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Jump to date")
        .sheet(isPresented: $isDatePickerPresented) {
            JumpToDateSheet(date: binding, isPresented: $isDatePickerPresented)
        }
    }

    private func jumpPillLabel(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = Calendar.current.isDate(date, equalTo: Date(), toGranularity: .year)
            ? "MMM d"
            : "MMM d, yyyy"
        return formatter.string(from: date)
    }

    private var calendar: Calendar { Calendar.current }

    private var anchorDate: Date {
        calendar.startOfDay(for: jumpToDate?.wrappedValue ?? Date())
    }

    private var showsByDate: [Date: [Components.Schemas.Show]] {
        Dictionary(grouping: shows) { calendar.startOfDay(for: $0.date) }
    }

    private var groupedShows: [(date: Date, shows: [Components.Schemas.Show])] {
        showsByDate
            .map { (date: $0.key, shows: $0.value.sorted { $0.date < $1.date }) }
            .sorted { $0.date < $1.date }
    }

    private var dateRange: [Date] {
        let start = anchorDate
        return (0..<7).compactMap { offset in
            calendar.date(byAdding: .day, value: offset, to: start)
        }
    }
}


private struct ShowsCalendarWeekStrip: View {
    @Environment(\.appTheme) private var theme

    let dateRange: [Date]
    let showsByDate: [Date: [Components.Schemas.Show]]
    @Binding var selectedDates: Set<Date>

    private var calendar: Calendar { Calendar.current }
    private var today: Date { calendar.startOfDay(for: Date()) }

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(dateRange, id: \.self) { date in
                        let hasShow = !(showsByDate[date]?.isEmpty ?? true)
                        ShowsCalendarDayChip(
                            date: date,
                            hasShow: hasShow,
                            isSelected: selectedDates.contains(date),
                            isToday: calendar.isDate(date, inSameDayAs: today)
                        )
                        .id(date)
                        .onTapGesture {
                            guard hasShow else { return }
                            if selectedDates.contains(date) {
                                selectedDates.remove(date)
                            } else {
                                selectedDates.insert(date)
                            }
                        }
                    }
                }
                .padding(.vertical, 2)
                .padding(.horizontal, 2)
            }
            .onAppear {
                let target = firstShowDate ?? today
                DispatchQueue.main.async {
                    proxy.scrollTo(target, anchor: .leading)
                }
            }
        }
    }

    private var firstShowDate: Date? {
        dateRange.first { !(showsByDate[$0]?.isEmpty ?? true) }
    }
}

private struct ShowsCalendarDayChip: View {
    @Environment(\.appTheme) private var theme

    let date: Date
    let hasShow: Bool
    let isSelected: Bool
    let isToday: Bool

    var body: some View {
        VStack(spacing: 4) {
            Text(weekdayLabel)
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(textColor.opacity(0.78))
                .textCase(.uppercase)
            Text(dayLabel)
                .font(.system(size: 18, weight: .bold))
                .foregroundStyle(textColor)
        }
        .frame(width: 44, height: 58)
        .background(background)
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(borderColor, lineWidth: isToday && !isSelected ? 1.5 : 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .opacity(hasShow ? 1.0 : 0.45)
    }

    private var weekdayLabel: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEE"
        return String(formatter.string(from: date).prefix(3))
    }

    private var dayLabel: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "d"
        return formatter.string(from: date)
    }

    @ViewBuilder
    private var background: some View {
        let laughTrack = theme.laughTrackTokens
        if isSelected {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(laughTrack.colors.accentStrong.opacity(0.18))
        } else {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(laughTrack.colors.surfaceElevated)
        }
    }

    private var borderColor: Color {
        let laughTrack = theme.laughTrackTokens
        if isSelected {
            return laughTrack.colors.accentStrong
        } else if isToday {
            return laughTrack.colors.accent
        }
        return laughTrack.colors.borderSubtle
    }

    private var textColor: Color {
        theme.laughTrackTokens.colors.textPrimary
    }
}

private struct ShowsCalendarDaySection: View {
    @Environment(\.appTheme) private var theme

    let date: Date
    let shows: [Components.Schemas.Show]
    let onSelectShow: (Int) -> Void
    let isNearMe: ((Components.Schemas.Show) -> Bool)?
    let thumbnailImageURL: ((Components.Schemas.Show) -> String?)?

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: 8) {
            Text(headerText)
                .font(laughTrack.typography.metadata.weight(.semibold))
                .foregroundStyle(laughTrack.colors.textSecondary)
                .textCase(.uppercase)

            VStack(spacing: 8) {
                ForEach(shows, id: \.id) { show in
                    Button {
                        onSelectShow(show.id)
                    } label: {
                        ShowsCalendarShowCard(
                            show: show,
                            isNearMe: isNearMe?(show) ?? false,
                            thumbnailURLString: thumbnailImageURL?(show) ?? show.imageUrl
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var headerText: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEE · MMM d"
        return formatter.string(from: date)
    }
}

private struct ShowsCalendarShowCard: View {
    @Environment(\.appTheme) private var theme

    let show: Components.Schemas.Show
    let isNearMe: Bool
    let thumbnailURLString: String

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(timeText)
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
                if let zone = timezoneAbbreviation {
                    Text(zone)
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(laughTrack.colors.textSecondary)
                }
            }
            .frame(width: 58, alignment: .leading)

            thumbnail

            VStack(alignment: .leading, spacing: 4) {
                Text(ShowRow.listTitle(for: show))
                    .font(laughTrack.typography.body.weight(.semibold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)

                HStack(spacing: 8) {
                    if isNearMe {
                        Image(systemName: "location.fill")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundStyle(laughTrack.colors.accentStrong)
                            .accessibilityLabel("Near you")
                    }
                    if let metadata = metadataLabel {
                        Text(metadata)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            Image(systemName: "chevron.right")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(laughTrack.colors.textSecondary)
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
    }

    @ViewBuilder
    private var thumbnail: some View {
        let laughTrack = theme.laughTrackTokens
        let url = URL.normalizedExternalURL(thumbnailURLString.trimmingCharacters(in: .whitespacesAndNewlines))

        Group {
            if let url {
                CachedAsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    Rectangle().fill(laughTrack.colors.surfaceMuted)
                } error: { _ in
                    placeholderThumbnail
                }
            } else {
                placeholderThumbnail
            }
        }
        .frame(width: 44, height: 44)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
    }

    @ViewBuilder
    private var placeholderThumbnail: some View {
        let laughTrack = theme.laughTrackTokens
        ZStack {
            Rectangle().fill(laughTrack.colors.surfaceMuted)
            Image(systemName: "ticket.fill")
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(laughTrack.colors.accentStrong)
        }
    }

    private var timeText: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        if let zoneID = show.timezone, let zone = TimeZone(identifier: zoneID) {
            formatter.timeZone = zone
        }
        return formatter.string(from: show.date)
    }

    private var timezoneAbbreviation: String? {
        guard let zoneID = show.timezone, let zone = TimeZone(identifier: zoneID) else { return nil }
        return zone.abbreviation(for: show.date)
    }

    private var metadataLabel: String? {
        if show.soldOut == true {
            return "Sold out"
        }
        return ShowRow.priceLabel(for: show)
    }
}
