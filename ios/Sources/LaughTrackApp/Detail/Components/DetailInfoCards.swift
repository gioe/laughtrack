import SwiftUI
import LaughTrackBridge

enum DetailDescriptionText {
    static func normalized(_ value: String?) -> String? {
        guard var text = value else { return nil }
        // Listing and feed descriptions may carry HTML. Display only plain text,
        // preserving paragraph breaks.
        text = text.replacingOccurrences(of: "(?is)<(script|style)\\b[^>]*>.*?</\\1\\s*>", with: "", options: .regularExpression)
        text = text.replacingOccurrences(of: "(?i)<\\s*br\\s*/?\\s*>", with: "\n", options: .regularExpression)
        text = text.replacingOccurrences(of: "(?i)</\\s*(p|div|li|h[1-6])\\s*>", with: "\n\n", options: .regularExpression)
        text = text.replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
        let entities = ["amp": "&", "quot": "\"", "apos": "'", "lt": "<", "gt": ">", "nbsp": " ",
                        "hellip": "…", "mdash": "—", "ndash": "–", "rsquo": "’", "lsquo": "‘", "ldquo": "“", "rdquo": "”"]
        if let pattern = try? NSRegularExpression(pattern: "&(#x[0-9a-f]+|#[0-9]+|[a-z]+);", options: .caseInsensitive) {
            for match in pattern.matches(in: text, range: NSRange(text.startIndex..., in: text)).reversed() {
                guard let range = Range(match.range, in: text), let keyRange = Range(match.range(at: 1), in: text) else { continue }
                let key = String(text[keyRange]).lowercased()
                let number = key.hasPrefix("#x") ? UInt32(key.dropFirst(2), radix: 16)
                    : key.hasPrefix("#") ? UInt32(key.dropFirst()) : nil
                let replacement = entities[key] ?? number.flatMap(UnicodeScalar.init).map(String.init)
                if let replacement { text.replaceSubrange(range, with: replacement) }
            }
        }
        return text.replacingOccurrences(of: "\n{3,}", with: "\n\n", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
    }
}

struct DetailInfoRow {
    let label: String
    let value: String?
}

struct DetailInfoCard: View {
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
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
                        (dynamicTypeSize.isAccessibilitySize ? AnyLayout(VStackLayout(alignment: .leading, spacing: 4)) : AnyLayout(HStackLayout(alignment: .top))) {
                            Text(row.label)
                                .font(laughTrack.typography.metadata)
                                .foregroundStyle(laughTrack.colors.textSecondary)
                                .frame(width: dynamicTypeSize.isAccessibilitySize ? nil : 72, alignment: .leading)
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
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.appTheme) private var theme

    let eyebrow: String?
    let title: String?
    let text: String
    var isCollapsible: Bool = false
    var collapsedLineLimit: Int = 4

    @State private var isExpanded = false

    private var showsToggle: Bool {
        isCollapsible && Self.shouldCollapse(text: text, lineLimit: collapsedLineLimit)
    }

    static func shouldCollapse(text: String, lineLimit: Int = 4) -> Bool {
        text.count > 220 || text.components(separatedBy: .newlines).count > lineLimit
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
                    .animation(reduceMotion ? nil : .easeInOut(duration: 0.18), value: isExpanded)

                if showsToggle {
                    Button {
                        withAnimation(reduceMotion ? nil : .easeInOut(duration: 0.18)) {
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
                        .frame(minHeight: 44)
                        .contentShape(Rectangle())
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
