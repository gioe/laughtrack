import Foundation

@MainActor
final class SearchRootModel: ObservableObject {
    enum Pivot: String, CaseIterable, Identifiable {
        case shows
        case comedians
        case clubs

        var id: String { rawValue }
        var title: String { rawValue.capitalized }
    }

    @Published var query = ""
    @Published var activePivot: Pivot = .shows
    @Published var selectedShortcut: String? = "Near Me"
}
