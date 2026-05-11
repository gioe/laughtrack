import SwiftUI

#if canImport(UIKit)
import UIKit
import SafariServices

struct SafariView: UIViewControllerRepresentable {
    let url: URL
    var preferredBarTintColor: UIColor?
    var preferredControlTintColor: UIColor?

    func makeUIViewController(context: Context) -> SFSafariViewController {
        let configuration = SFSafariViewController.Configuration()
        configuration.entersReaderIfAvailable = false
        configuration.barCollapsingEnabled = true
        let controller = SFSafariViewController(url: url, configuration: configuration)
        controller.preferredBarTintColor = preferredBarTintColor
        controller.preferredControlTintColor = preferredControlTintColor
        controller.dismissButtonStyle = .done
        return controller
    }

    func updateUIViewController(_ uiViewController: SFSafariViewController, context: Context) {}
}

extension View {
    /// Presents an SFSafariViewController in a sheet bound to the optional URL.
    /// Setting the binding to `nil` dismisses the sheet.
    func safariSheet(url: Binding<URL?>) -> some View {
        modifier(SafariSheetModifier(url: url))
    }
}

private struct SafariSheetModifier: ViewModifier {
    @Binding var url: URL?
    @Environment(\.appTheme) private var theme

    func body(content: Content) -> some View {
        content.sheet(item: Binding(
            get: { url.map(IdentifiedURL.init) },
            set: { url = $0?.url }
        )) { item in
            SafariView(
                url: item.url,
                preferredBarTintColor: UIColor(theme.laughTrackTokens.colors.surface),
                preferredControlTintColor: UIColor(theme.laughTrackTokens.colors.accent)
            )
            .ignoresSafeArea()
        }
    }
}

private struct IdentifiedURL: Identifiable {
    let url: URL
    var id: URL { url }
}
#else
extension View {
    /// No-op fallback when UIKit is not available (e.g. macOS host builds).
    /// Production iOS builds use the SFSafariViewController-backed implementation above.
    func safariSheet(url: Binding<URL?>) -> some View { self }
}
#endif
