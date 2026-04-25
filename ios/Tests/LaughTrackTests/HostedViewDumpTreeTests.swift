#if canImport(UIKit)
import Foundation
import SwiftUI
import Testing
import UIKit

@Suite("HostedView dumpAccessibilityTree")
@MainActor
struct HostedViewDumpTreeTests {
    @Test("dumps the rooted UIView tree with type, identifier, and label")
    func dumpIncludesTypeIdentifierAndLabel() {
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
        // SwiftUI's Text surfaces as an accessibility element (not a UIView
        // subview), so the helper must walk `accessibilityElements` to see it.
        #expect(dump.contains("<element>"))
        #expect(dump.contains("id='greeting'"))
        #expect(dump.contains("label='Hello, world!'"))
        #expect(dump.contains("id='primary-action'"))
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
        #expect(onDisk.contains("id='writable-target'"))
    }
}
#endif
