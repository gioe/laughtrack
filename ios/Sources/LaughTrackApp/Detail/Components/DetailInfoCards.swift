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
            }
        }
    }
}

struct DetailTextCard: View {
    @Environment(\.appTheme) private var theme

    let eyebrow: String?
    let title: String
    let text: String

    var body: some View {
        LaughTrackCard {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(eyebrow: eyebrow, title: title)
                Text(text)
                    .font(theme.laughTrackTokens.typography.body)
                    .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
            }
        }
    }
}
