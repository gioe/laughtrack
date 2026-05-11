import SwiftUI

/// Sheet-based date picker used wherever the user picks a "from-this-date-forward"
/// calendar anchor — comedian/club detail calendars and the shows search filter.
/// Pass `onClear` to surface a leading "Any date" toolbar action that clears
/// the date filter; omit it when there's no clearable state (e.g. detail pages
/// which always have a from-date).
struct JumpToDateSheet: View {
    @Binding var date: Date
    @Binding var isPresented: Bool
    var title: String = "Jump to date"
    var prompt: String = "Show shows from"
    var onClear: (() -> Void)? = nil

    @State private var draft: Date

    init(
        date: Binding<Date>,
        isPresented: Binding<Bool>,
        title: String = "Jump to date",
        prompt: String = "Show shows from",
        onClear: (() -> Void)? = nil
    ) {
        _date = date
        _isPresented = isPresented
        self.title = title
        self.prompt = prompt
        self.onClear = onClear
        _draft = State(initialValue: date.wrappedValue)
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                DatePicker(
                    prompt,
                    selection: $draft,
                    in: Date()...,
                    displayedComponents: [.date]
                )
                .datePickerStyle(.graphical)
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
                        isPresented = false
                    }
                    .fontWeight(.semibold)
                }
            }
        }
        .presentationDetents([.medium, .large])
    }
}
