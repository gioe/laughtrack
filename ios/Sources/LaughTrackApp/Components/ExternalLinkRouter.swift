import SwiftUI

/// Decides whether a URL should open in an in-app `SFSafariViewController`
/// or be handed off to the system via `openURL`.
///
/// Routing rules:
///   - `http(s)` URLs → in-app SafariView (set `presentedURL`)
///   - `http(s)://maps.apple.com` and `maps://`        → system Maps via openURL
///   - `tel:`, `mailto:`, `sms:`, `facetime:`, custom schemes → openURL
enum ExternalLinkRouter {
    static func route(_ url: URL, presentedURL: Binding<URL?>, openURL: OpenURLAction) {
        if shouldUseSystem(url) {
            openURL(url)
        } else {
            presentedURL.wrappedValue = url
        }
    }

    static func shouldUseSystem(_ url: URL) -> Bool {
        let scheme = (url.scheme ?? "").lowercased()
        switch scheme {
        case "http", "https":
            return isAppleMaps(url)
        default:
            // tel, mailto, sms, facetime, maps, custom — let the system handle it.
            return true
        }
    }

    private static func isAppleMaps(_ url: URL) -> Bool {
        guard let host = url.host?.lowercased() else { return false }
        return host == "maps.apple.com" || host.hasSuffix(".maps.apple.com")
    }
}
