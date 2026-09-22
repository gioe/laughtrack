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
    var detectsWebLinks: Bool = false

    @State var isExpanded = false

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

                Text(detectsWebLinks ? PodcastEpisodeNotes.attributedText(text) : AttributedString(text))
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


/// Feed content is converted to native text, never rendered by an HTML engine.
/// Link detection is opt-in so other detail descriptions retain their behavior.
enum PodcastEpisodeNotes {
    static func text(_ raw: String?) -> String? {
        guard var value = raw else { return nil }
        // Retain destinations that would otherwise disappear with anchor tags.
        let anchors = try? NSRegularExpression(
            pattern: #"<a\b[^>]*\bhref\s*=\s*(?:"([^"]*)"|'([^']*)')[^>]*>(.*?)</a\s*>"#,
            options: [.caseInsensitive, .dotMatchesLineSeparators]
        )
        for match in anchors?.matches(in: value, range: NSRange(value.startIndex..., in: value)).reversed() ?? [] {
            guard let range = Range(match.range, in: value),
                  let labelRange = Range(match.range(at: 3), in: value),
                  let hrefRange = Range(match.range(at: match.range(at: 1).location == NSNotFound ? 2 : 1), in: value)
            else { continue }
            let label = String(value[labelRange])
            let href = String(value[hrefRange])
            value.replaceSubrange(range, with: label == href ? label : "\(label) (\(href))")
        }
        return DetailDescriptionText.normalized(value)
    }

    static func webURL(_ raw: String) -> URL? {
        guard !raw.isEmpty,
              raw.rangeOfCharacter(from: .whitespacesAndNewlines.union(.controlCharacters)) == nil,
              raw.range(of: #"%(?![0-9a-fA-F]{2})"#, options: .regularExpression) == nil,
              let components = URLComponents(string: raw),
              let scheme = components.scheme?.lowercased(), ["http", "https"].contains(scheme),
              let host = components.host, !host.isEmpty,
              components.user == nil, components.password == nil,
              components.port.map({ (1...65535).contains($0) }) ?? true,
              let url = components.url
        else { return nil }
        // URLComponents can encode malformed host characters rather than reject
        // them. Accept DNS/IDN names and bracketed IPv6, never repaired whitespace.
        if host.hasPrefix("[") && host.hasSuffix("]") {
            guard host.dropFirst().dropLast().allSatisfy({ $0.isHexDigit || $0 == ":" || $0 == "." }) else { return nil }
        } else {
            let labels = host.split(separator: ".", omittingEmptySubsequences: false)
            guard labels.allSatisfy({ label in
                !label.isEmpty && label.first != "-" && label.last != "-"
                    && label.allSatisfy({ $0.isLetter || $0.isNumber || $0 == "-" })
            }) else { return nil }
        }
        return url
    }

    static func attributedText(_ text: String) -> AttributedString {
        var result = AttributedString(text)
        // Start from literal text: Markdown and unsupported schemes never gain
        // hidden destinations. Only visible, explicit web URLs become links.
        let pattern = try? NSRegularExpression(pattern: #"(?i)(?<![\p{L}\p{N}_:/])https?://[^\s<>"']+"#)
        for match in pattern?.matches(in: text, range: NSRange(text.startIndex..., in: text)) ?? [] {
            guard let matchedRange = Range(match.range, in: text) else { continue }
            var candidate = String(text[matchedRange])
            while let last = candidate.last {
                if ".,;!?".contains(last) {
                    candidate.removeLast()
                } else if let opener = [")": "(", "]": "[", "}": "{"][String(last)],
                          candidate.filter({ String($0) == String(last) }).count > candidate.filter({ String($0) == opener }).count {
                    candidate.removeLast()
                } else { break }
            }
            guard let url = webURL(candidate) else { continue }
            let end = text.index(matchedRange.lowerBound, offsetBy: candidate.count)
            guard let lower = AttributedString.Index(matchedRange.lowerBound, within: result),
                  let upper = AttributedString.Index(end, within: result) else { continue }
            result[lower..<upper].link = url
        }
        return result
    }
}
