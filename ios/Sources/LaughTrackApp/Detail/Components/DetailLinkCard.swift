import Foundation
import SwiftUI
import LaughTrackBridge

struct DetailLink {
    let title: String
    let url: URL?
}

struct DetailLinkCard: View {
    @Environment(\.appTheme) private var theme

    let eyebrow: String?
    let title: String
    let subtitle: String?
    let links: [DetailLink]
    let openURL: (URL) -> Void

    var body: some View {
        LaughTrackCard {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(eyebrow: eyebrow, title: title, subtitle: subtitle)
                ForEach(Array(links.enumerated()), id: \.offset) { _, link in
                    if let url = link.url {
                        LaughTrackButton(link.title, systemImage: "arrow.up.right", tone: .secondary) {
                            openURL(url)
                        }
                    }
                }
                if links.allSatisfy({ $0.url == nil }) {
                    EmptyCard(message: "No public links are available yet.")
                }
            }
        }
    }
}
