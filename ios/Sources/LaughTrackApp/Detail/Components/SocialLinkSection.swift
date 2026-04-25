import Foundation
import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge

struct SocialLink: Identifiable {
    let id = UUID()
    let label: String
    let url: URL

    static func links(from socialData: Components.Schemas.SocialData) -> [SocialLink] {
        [
            ("Instagram", socialData.instagramAccount?.socialURL(host: "instagram.com")),
            ("TikTok", socialData.tiktokAccount?.socialURL(host: "tiktok.com/@")),
            ("YouTube", socialData.youtubeAccount?.socialURL(host: "youtube.com/@")),
            ("Website", URL.normalizedExternalURL(socialData.website)),
            ("Linktree", URL.normalizedExternalURL(socialData.linktree))
        ]
        .compactMap { label, url in
            guard let url else { return nil }
            return SocialLink(label: label, url: url)
        }
    }
}

struct SocialLinkSection: View {
    let socialData: Components.Schemas.SocialData
    let openURL: (URL) -> Void

    var body: some View {
        let links = SocialLink.links(from: socialData)

        return LaughTrackCard {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(
                    eyebrow: "Follow",
                    title: "Links",
                    subtitle: "Social and web destinations use the same shared CTA treatment as the rest of the app."
                )
                if links.isEmpty {
                    EmptyCard(message: "No public links are available yet.")
                } else {
                    ForEach(links) { link in
                        LaughTrackButton(link.label, systemImage: "arrow.up.right", tone: .secondary) {
                            openURL(link.url)
                        }
                    }
                }
            }
        }
    }
}
