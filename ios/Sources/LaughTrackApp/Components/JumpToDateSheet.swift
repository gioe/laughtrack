import SwiftUI
import LaughTrackBridge

/// Sheet-based date picker for single-date callers — comedian/club detail
/// calendars and the shows-search date filter. Pass `onClear` to surface a
/// leading "Any date" toolbar action that clears the date filter; omit when
/// there is no clearable state.
///
/// `showsByDate` paints accent dots on days with shows; pass an empty map for
/// callers that don't have a per-day count available (e.g. the shows-discovery
/// model). `onApply` fires when the user taps Apply so callers can mark the
/// date filter as active.
struct JumpToDateSheet: View {
    @Binding var date: Date
    @Binding var isPresented: Bool
    var title: String
    var showsByDate: [Date: Int]
    var onApply: ((Date) -> Void)?
    var onClear: (() -> Void)?

    @State private var draft: Date

    init(
        date: Binding<Date>,
        isPresented: Binding<Bool>,
        title: String = "Jump to date",
        showsByDate: [Date: Int] = [:],
        onApply: ((Date) -> Void)? = nil,
        onClear: (() -> Void)? = nil
    ) {
        _date = date
        _isPresented = isPresented
        self.title = title
        self.showsByDate = showsByDate
        self.onApply = onApply
        self.onClear = onClear
        _draft = State(initialValue: Calendar.current.startOfDay(for: date.wrappedValue))
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                MonthCalendarView(
                    selection: .single($draft),
                    showsByDate: showsByDate,
                    minimumDate: Calendar.current.startOfDay(for: Date())
                )
                .padding(.horizontal)
                Spacer()
            }
            .padding(.top)
            .navigationTitle(title)
            .modifier(InlineNavigationTitle())
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { isPresented = false }
                }
                #if os(iOS)
                if let onClear {
                    ToolbarItem(placement: .topBarLeading) {
                        Button("Any date") {
                            onClear()
                            isPresented = false
                        }
                    }
                }
                #endif
                ToolbarItem(placement: .confirmationAction) {
                    Button("Apply") {
                        date = draft
                        onApply?(draft)
                        isPresented = false
                    }
                    .fontWeight(.semibold)
                }
            }
        }
        .presentationDetents([.medium, .large])
    }
}
