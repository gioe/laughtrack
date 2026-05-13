import SwiftUI

/// Shared trigger for filter pills that open a sheet — Location, Date, and
/// any future "tap to edit" affordance. Paired with `PillDropdownTrigger`,
/// which handles the other behavior class: inline dropdowns that blur the
/// background and reveal options in place (Distance, Sort).
///
/// Visually rendered as a `LaughTrackBrowseChip`. Tone shifts to `.selected`
/// when the filter is active so the user can see which constraints are
/// currently applied.
struct PillSheetTrigger: View {
    let title: String
    let systemImage: String
    var isActive: Bool = false
    var accessibilityLabel: String? = nil
    var accessibilityHint: String? = nil
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            LaughTrackBrowseChip(
                title,
                systemImage: systemImage,
                tone: isActive ? .accent : .neutral
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel(accessibilityLabel ?? title)
        .accessibilityHint(accessibilityHint ?? "")
    }
}
