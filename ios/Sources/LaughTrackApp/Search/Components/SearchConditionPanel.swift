import LaughTrackCore
import SwiftUI

struct SearchConditionPanel: View {
    @ObservedObject var model: SearchRootModel
    @ObservedObject var showsModel: ShowsDiscoveryModel
    let onShortcutSelected: () -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        LaughTrackCard(density: .compact) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.rowGap) {
                LaughTrackSearchField(
                    placeholder: model.activePivot.queryPrompt,
                    text: $model.query
                )

                shortcutRow
                pivotRow

                if model.activePivot == .shows {
                    Divider()
                        .padding(.vertical, theme.spacing.xs)

                    ShowsConditionControls(model: showsModel)
                }
            }
        }
    }

    private var shortcutRow: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: theme.spacing.sm) {
                ForEach(["Near Me", "Tonight", "This Week"], id: \.self) { shortcut in
                    Button {
                        model.selectShortcut(shortcut)
                        onShortcutSelected()
                    } label: {
                        LaughTrackBrowseChip(
                            shortcut,
                            systemImage: shortcutSystemImage(for: shortcut),
                            tone: shortcutTone(for: shortcut)
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var pivotRow: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: theme.spacing.sm) {
                ForEach(SearchRootModel.Pivot.allCases) { pivot in
                    Button {
                        model.activePivot = pivot
                    } label: {
                        LaughTrackBrowseChip(
                            pivot.title,
                            systemImage: pivotSystemImage(for: pivot),
                            tone: model.activePivot == pivot ? .selected : .neutral
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func shortcutTone(for shortcut: String) -> LaughTrackBrowseChipTone {
        model.selectedShortcut == shortcut ? .selected : .neutral
    }

    private func shortcutSystemImage(for shortcut: String) -> String {
        switch shortcut {
        case "Tonight":
            return "moon.stars"
        case "This Week":
            return "calendar"
        default:
            return "location"
        }
    }

    private func pivotSystemImage(for pivot: SearchRootModel.Pivot) -> String {
        switch pivot {
        case .shows:
            return "music.mic"
        case .comedians:
            return "person.2"
        case .clubs:
            return "building.2"
        }
    }
}

struct ShowsConditionControls: View {
    @Environment(\.appTheme) private var theme

    @ObservedObject var model: ShowsDiscoveryModel

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.md) {
            VStack(alignment: .leading, spacing: theme.spacing.sm) {
                LaughTrackSearchField(placeholder: "10012", text: $model.zipCodeDraft) {
                    if let activeNearbyPreference = model.activeNearbyPreference {
                        NearbyPreferenceAccessory(preference: activeNearbyPreference)
                    }
                }
                    .modifier(SearchFieldInputBehavior())
                    #if os(iOS)
                    .keyboardType(UIKeyboardType.numberPad)
                    #endif
                    .onSubmit {
                        _ = model.applyManualZip()
                    }

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: theme.spacing.sm) {
                        CurrentLocationButton(isLoading: model.isResolvingCurrentLocation) {
                            await model.useCurrentLocation()
                        }

                        if model.activeNearbyPreference != nil {
                            LaughTrackButton("Clear", systemImage: "location.slash", tone: .tertiary, density: .compact, fullWidth: false) {
                                model.clearLocation()
                            }
                        }
                    }
                }

                if let nearbyStatusMessage = model.nearbyStatusMessage {
                    InlineStatusMessage(message: nearbyStatusMessage)
                }
            }

            HStack(spacing: theme.spacing.sm) {
                Menu {
                    Picker("Sort", selection: $model.sort) {
                        ForEach(ShowSortOption.allCases) { option in
                            Text(option.title).tag(option)
                        }
                    }
                } label: {
                    LaughTrackBrowseChip(
                        "Sort: \(model.sort.title)",
                        systemImage: "arrow.up.arrow.down",
                        tone: .neutral
                    )
                }

                if model.activeNearbyPreference != nil {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: theme.spacing.sm) {
                            ForEach(ShowDistanceOption.allCases) { option in
                                Button {
                                    model.distance = option
                                } label: {
                                    LaughTrackBrowseChip(
                                        option.title,
                                        tone: model.distance == option ? .selected : .neutral
                                    )
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                }
            }

            VStack(alignment: .leading, spacing: theme.spacing.sm) {
                Toggle("Use date range", isOn: $model.useDateRange)
                    .font(laughTrack.typography.body)
                    .tint(laughTrack.colors.accent)

                if model.useDateRange {
                    VStack(spacing: theme.spacing.md) {
                        DatePicker("From", selection: $model.fromDate, displayedComponents: .date)
                        DatePicker(
                            "To",
                            selection: Binding(
                                get: { max(model.toDate, model.fromDate) },
                                set: { model.toDate = max($0, model.fromDate) }
                            ),
                            in: model.fromDate...,
                            displayedComponents: .date
                        )
                    }
                    .font(laughTrack.typography.body)
                }
            }
        }
    }
}

private struct NearbyPreferenceAccessory: View {
    @Environment(\.appTheme) private var theme

    let preference: NearbyPreference

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.xs) {
            Image(systemName: preference.source == .manual ? "keyboard" : "location.fill")
                .font(.system(size: theme.iconSizes.sm, weight: .semibold))

            Text("\(sourceTitle) · \(preference.distanceMiles) mi")
                .font(laughTrack.typography.metadata)
                .lineLimit(1)
        }
        .foregroundStyle(laughTrack.colors.accentStrong)
        .padding(.horizontal, laughTrack.browseDensity.chipHorizontalPadding)
        .padding(.vertical, laughTrack.browseDensity.chipVerticalPadding)
        .background(laughTrack.colors.highlight.opacity(0.95))
        .overlay(
            Capsule(style: .continuous)
                .stroke(laughTrack.colors.borderStrong.opacity(0.45), lineWidth: 1)
        )
        .clipShape(Capsule(style: .continuous))
        .accessibilityLabel("\(accessibilitySource), \(preference.zipCode), \(preference.distanceMiles) miles")
    }

    private var sourceTitle: String {
        preference.source == .manual ? "Manual" : "Device"
    }

    private var accessibilitySource: String {
        preference.source == .manual ? "Manually entered ZIP" : "Device-resolved ZIP"
    }
}

private struct CurrentLocationButton: View {
    let isLoading: Bool
    let action: () async -> Void

    var body: some View {
        LaughTrackButton(
            isLoading ? "Finding ZIP…" : "Use Current Location",
            systemImage: isLoading ? nil : "location.circle",
            tone: .secondary,
            density: .compact,
            fullWidth: false
        ) {
            Task {
                await action()
            }
        }
        .disabled(isLoading)
        .overlay(alignment: .trailing) {
            if isLoading {
                ProgressView()
                    .padding(.trailing, 12)
            }
        }
    }
}
