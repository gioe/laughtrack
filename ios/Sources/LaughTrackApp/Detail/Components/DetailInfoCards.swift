import SwiftUI
import LaughTrackBridge

struct DetailInfoRow {
    let label: String
    let value: String?
}

struct DetailInfoCard: View {
    @Environment(\.appTheme) private var theme

    let eyebrow: String?
    let title: String
    let subtitle: String?
    let rows: [DetailInfoRow]
    var links: [DetailLink] = []
    var openURL: ((URL) -> Void)?

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let visibleRows = rows.filter { ($0.value?.isEmpty == false) }

        return LaughTrackCard {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(eyebrow: eyebrow, title: title, subtitle: subtitle)
                if visibleRows.isEmpty {
                    EmptyCard(message: "Details will appear here when LaughTrack has them.")
                } else {
                    ForEach(Array(visibleRows.enumerated()), id: \.offset) { _, row in
                        HStack(alignment: .top) {
                            Text(row.label)
                                .font(laughTrack.typography.metadata)
                                .foregroundStyle(laughTrack.colors.textSecondary)
                                .frame(width: 72, alignment: .leading)
                            Text(row.value ?? "")
                                .font(laughTrack.typography.body)
                                .foregroundStyle(laughTrack.colors.textPrimary)
                        }
                    }
                }

                if let openURL {
                    ForEach(Array(links.enumerated()), id: \.offset) { _, link in
                        if let url = link.url {
                            LaughTrackButton(link.title, systemImage: "arrow.up.right", tone: .secondary) {
                                openURL(url)
                            }
                        }
                    }
                }
            }
        }
    }
}

struct DetailTextCard: View {
    @Environment(\.appTheme) private var theme

    let eyebrow: String?
    let title: String?
    let text: String
    var isCollapsible: Bool = false
    var collapsedLineLimit: Int = 4

    @State private var isExpanded = false

    private var showsToggle: Bool {
        isCollapsible && text.count > 220
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        LaughTrackCard {
            VStack(alignment: .leading, spacing: 12) {
                header

                Text(text)
                    .font(laughTrack.typography.body)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(showsToggle && !isExpanded ? collapsedLineLimit : nil)
                    .animation(.easeInOut(duration: 0.18), value: isExpanded)

                if showsToggle {
                    Button {
                        withAnimation(.easeInOut(duration: 0.18)) {
                            isExpanded.toggle()
                        }
                    } label: {
                        HStack(spacing: 4) {
                            Text(isExpanded ? "Show less" : "Show more")
                                .font(laughTrack.typography.metadata.weight(.semibold))
                            Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                                .font(.system(size: 11, weight: .semibold))
                        }
                        .foregroundStyle(laughTrack.colors.accent)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(isExpanded ? "Collapse description" : "Expand description")
                }
            }
        }
    }

    @ViewBuilder
    private var header: some View {
        let laughTrack = theme.laughTrackTokens

        if let title {
            LaughTrackSectionHeader(eyebrow: eyebrow, title: title)
        } else if let eyebrow {
            Text(eyebrow)
                .font(laughTrack.typography.eyebrow)
                .foregroundStyle(laughTrack.colors.accent)
                .textCase(.uppercase)
        }
    }
}
