#if canImport(UIKit)
import Foundation
import SwiftUI
import Testing
import UIKit

@Suite("HostedView dumpAccessibilityTree")
@MainActor
struct HostedViewDumpTreeTests {
    @Test("dumps the rooted UIView tree")
    func dumpIncludesRootViewTree() {
        let host = HostedView(
            VStack {
                Text("Hello, world!")
                    .accessibilityIdentifier("greeting")
                Button("Tap me") {}
                    .accessibilityIdentifier("primary-action")
            }
        )

        let dump = host.dumpAccessibilityTree()

        // Hosting controller's UIView is the root — the dump must lead with a
        // <view> node, not be empty.
        #expect(dump.hasPrefix("<view>"))
        #expect(dump.contains("_UIHostingView"))
    }

    @Test("writes the dump to the supplied path when provided")
    func dumpWritesToPathWhenSupplied() throws {
        let host = HostedView(
            Text("File-bound dump")
                .accessibilityIdentifier("writable-target")
        )

        let path = NSTemporaryDirectory()
            + "hosted-view-dump-\(UUID().uuidString).txt"
        defer { try? FileManager.default.removeItem(atPath: path) }

        let returned = host.dumpAccessibilityTree(writingTo: path)
        let onDisk = try String(contentsOfFile: path, encoding: .utf8)

        #expect(returned == onDisk)
        #expect(onDisk.hasPrefix("<view>"))
    }
}
#endif
