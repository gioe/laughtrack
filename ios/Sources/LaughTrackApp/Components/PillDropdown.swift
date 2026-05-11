import SwiftUI

enum PillDropdownLayout {
    static let pillWidth: CGFloat = 132
    static let pillHeight: CGFloat = 38
}

struct PillDropdownAnchorKey: PreferenceKey {
    static var defaultValue: [String: Anchor<CGRect>] = [:]
    static func reduce(value: inout [String: Anchor<CGRect>], nextValue: () -> [String: Anchor<CGRect>]) {
        value.merge(nextValue()) { _, new in new }
    }
}

struct PillDropdownTrigger<Option: Hashable & Identifiable>: View {
    @Environment(\.appTheme) private var theme

    let id: String
    let selected: Option
    let triggerLabel: (Option) -> String
    @Binding var openDropdownID: String?

    private var isExpanded: Bool { openDropdownID == id }

    var body: some View {
        Button {
            withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                openDropdownID = isExpanded ? nil : id
            }
        } label: {
            HStack(spacing: 6) {
                Text(triggerLabel(selected))
                    .font(theme.laughTrackTokens.typography.metadata)
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
                Image(systemName: "chevron.down")
                    .font(.system(size: 10, weight: .bold))
                    .rotationEffect(.degrees(isExpanded ? 180 : 0))
            }
            .foregroundStyle(theme.laughTrackTokens.colors.textInverse)
            .frame(width: PillDropdownLayout.pillWidth, height: PillDropdownLayout.pillHeight)
            .background(
                Capsule(style: .continuous).fill(theme.laughTrackTokens.colors.textPrimary)
            )
            .opacity(isExpanded ? 0 : 1)
        }
        .buttonStyle(.plain)
        .transformAnchorPreference(key: PillDropdownAnchorKey.self, value: .bounds) { value, anchor in
            value[id] = anchor
        }
        .accessibilityLabel(triggerLabel(selected))
        .accessibilityHint(isExpanded ? "Tap to close options" : "Tap to choose another option")
    }
}

struct PillDropdownOverlay<Option: Hashable & Identifiable>: View {
    @Environment(\.appTheme) private var theme

    let id: String
    let options: [Option]
    @Binding var selected: Option
    let triggerLabel: (Option) -> String
    let optionLabel: (Option) -> String
    @Binding var openDropdownID: String?
    let anchors: [String: Anchor<CGRect>]
    let proxy: GeometryProxy

    private var isOpen: Bool { openDropdownID == id }

    var body: some View {
        if isOpen, let anchor = anchors[id] {
            let triggerFrame = proxy[anchor]

            ZStack(alignment: .topLeading) {
                Rectangle()
                    .fill(.ultraThinMaterial)
                    .opacity(0.5)
                    .ignoresSafeArea()
                    .contentShape(Rectangle())
                    .onTapGesture { dismiss() }

                VStack(alignment: .leading, spacing: 6) {
                    Button(action: dismiss) {
                        HStack(spacing: 6) {
                            Text(triggerLabel(selected))
                                .font(theme.laughTrackTokens.typography.metadata)
                                .lineLimit(1)
                                .minimumScaleFactor(0.75)
                            Image(systemName: "chevron.down")
                                .font(.system(size: 10, weight: .bold))
                                .rotationEffect(.degrees(180))
                        }
                        .foregroundStyle(theme.laughTrackTokens.colors.textInverse)
                        .frame(width: PillDropdownLayout.pillWidth, height: PillDropdownLayout.pillHeight)
                        .background(
                            Capsule(style: .continuous).fill(theme.laughTrackTokens.colors.textPrimary)
                        )
                    }
                    .buttonStyle(.plain)

                    ForEach(options.filter { $0 != selected }) { option in
                        Button {
                            withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                                selected = option
                                openDropdownID = nil
                            }
                        } label: {
                            Text(optionLabel(option))
                                .font(theme.laughTrackTokens.typography.metadata)
                                .lineLimit(1)
                                .minimumScaleFactor(0.75)
                                .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                                .frame(width: PillDropdownLayout.pillWidth, height: PillDropdownLayout.pillHeight)
                                .background(
                                    Capsule(style: .continuous)
                                        .fill(theme.laughTrackTokens.colors.surfaceElevated)
                                )
                                .overlay(
                                    Capsule(style: .continuous)
                                        .stroke(theme.laughTrackTokens.colors.borderSubtle, lineWidth: 1)
                                )
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel(optionLabel(option))
                        .transition(.opacity.combined(with: .move(edge: .top)))
                    }
                }
                .offset(x: triggerFrame.minX, y: triggerFrame.minY)
            }
            .transition(.opacity)
        }
    }

    private func dismiss() {
        withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
            openDropdownID = nil
        }
    }
}
