import Foundation
import Testing
@testable import LaughTrackApp

@Suite("Podcast episode notes")
struct PodcastEpisodeNotesTests {
    @Test("empty and markup-only notes are omitted", arguments: [nil, "", " \n\t ", "<p>&nbsp;</p>", "<script>alert('tracking')</script><style>p{color:red}</style>"] as [String?])
    func emptyNotes(_ raw: String?) {
        #expect(PodcastEpisodeNotes.text(raw) == nil)
    }

    @Test("short notes retain their complete text without disclosure")
    func shortNotes() throws {
        let text = try #require(PodcastEpisodeNotes.text("  Recorded live in Brooklyn.  "))
        #expect(text == "Recorded live in Brooklyn.")
        #expect(!DetailTextCard.shouldCollapse(text: text))
        #expect(String(PodcastEpisodeNotes.attributedText(text).characters) == text)
    }

    @Test("long notes keep the final paragraph and all attributed characters")
    func longNotes() throws {
        let raw = String(repeating: "A conversation about writing jokes and life on the road. ", count: 12)
            + "\n\nFinal paragraph: thank you for listening."
        let text = try #require(PodcastEpisodeNotes.text(raw))
        #expect(DetailTextCard.shouldCollapse(text: text))
        #expect(text.hasSuffix("Final paragraph: thank you for listening."))
        #expect(String(PodcastEpisodeNotes.attributedText(text).characters) == text)
    }

    @Test("multiline notes use the disclosure policy even below the character threshold")
    func multilineNotes() throws {
        let text = try #require(PodcastEpisodeNotes.text("First\nSecond\nThird\nFourth\nFifth"))
        #expect(text.count < 220)
        #expect(DetailTextCard.shouldCollapse(text: text))
        #expect(String(PodcastEpisodeNotes.attributedText(text).characters) == text)
    }

    @Test("HTML becomes paragraphs and decoded text without executable content")
    func htmlNotes() throws {
        let raw = "<p>Comedy &amp; conversation with &#233;very guest.</p><script>alert('tracking')</script><style>p{color:red}</style><p>Tickets &#36;25 &#x2014; Friday.<br>Thank you!</p>"
        let text = try #require(PodcastEpisodeNotes.text(raw))
        #expect(text == "Comedy & conversation with évery guest.\n\nTickets $25 — Friday.\nThank you!")
        #expect(!text.contains("tracking"))
        #expect(!text.contains("color:red"))
        #expect(String(PodcastEpisodeNotes.attributedText(text).characters) == text)
    }

    @Test("HTTP and HTTPS links are actionable without consuming sentence punctuation")
    func linksAndPunctuation() {
        let text = "Visit https://example.com/notes, then (http://example.org/episode). Thanks!"
        let attributed = PodcastEpisodeNotes.attributedText(text)
        #expect(String(attributed.characters) == text)
        let links = linkedRuns(attributed)
        #expect(links.map(\.text) == ["https://example.com/notes", "http://example.org/episode"])
        #expect(links.map { $0.url.absoluteString } == ["https://example.com/notes", "http://example.org/episode"])
    }

    @Test("Unicode text survives linking without corrupting character ranges")
    func unicodeNotes() {
        let text = "🎙️ Café — 東京: https://example.com/notes?q=caf%C3%A9&lang=ja — merci!"
        let attributed = PodcastEpisodeNotes.attributedText(text)
        #expect(String(attributed.characters) == text)
        let links = linkedRuns(attributed)
        #expect(links.count == 1)
        #expect(links.first?.text == "https://example.com/notes?q=caf%C3%A9&lang=ja")
        #expect(links.first?.url.absoluteString == "https://example.com/notes?q=caf%C3%A9&lang=ja")
    }

    @Test("explicit valid web destinations are accepted", arguments: [
        "https://example.com", "http://example.com/episode", "HTTPS://example.com/notes",
        "https://example.com:8443/notes?q=hello%20world#credits"
    ])
    func validDestinations(_ raw: String) {
        #expect(PodcastEpisodeNotes.webURL(raw) != nil)
    }

    @Test("unsupported and malformed destinations remain non-actionable", arguments: [
        "javascript:alert(1)", "mailto:hello@example.com", "ftp://example.com/file",
        "file:///tmp/notes", "data:text/html,hello", "/episodes/1", "//example.com/notes",
        "example.com/notes", "https://", "https:///episode", "https://?q=episode",
        "https://exa mple.com/notes", "https://example.com/a b", "https://example.com/\nnotes",
        "https://example.com/%", "https://example.com/%2", "https://example.com/%GG",
        "https://example.com:wrong/notes", "https://example.com:70000/notes", "https://example.com:-1/notes"
    ])
    func rejectedDestinations(_ raw: String) {
        #expect(PodcastEpisodeNotes.webURL(raw) == nil)
    }

    @Test("unsupported schemes and malformed web links preserve safe literal text")
    func invalidLinksStayText() {
        let text = "javascript:alert(1) javascript:https://example.com/path mailto:hello@example.com ftp://example.com/file /episodes/1 https://example.com/%GG https://example.com:wrong/notes"
        let attributed = PodcastEpisodeNotes.attributedText(text)
        #expect(String(attributed.characters) == text)
        #expect(linkedRuns(attributed).isEmpty)
    }

    @Test("literal markdown does not activate unsafe destinations or change text")
    func markdownStaysLiteral() {
        let text = "**Notes** [tap here](javascript:alert(1)) [email](mailto:hello@example.com) `literal code`"
        let attributed = PodcastEpisodeNotes.attributedText(text)
        #expect(String(attributed.characters) == text)
        #expect(linkedRuns(attributed).isEmpty)
        #expect(attributed.runs.allSatisfy { $0.inlinePresentationIntent == nil })
    }

    @Test("HTML anchor labels and destinations survive normalization as readable notes")
    func anchorNotes() throws {
        let text = try #require(PodcastEpisodeNotes.text("<p>Read <a href=\"https://example.com/notes\">Episode notes</a>.</p>"))
        #expect(text == "Read Episode notes (https://example.com/notes).")
        let attributed = PodcastEpisodeNotes.attributedText(text)
        #expect(String(attributed.characters) == text)
        #expect(linkedRuns(attributed).map(\.text) == ["https://example.com/notes"])
    }

    @Test("unsupported anchor destinations remain plain text")
    func unsafeAnchorNotes() throws {
        let text = try #require(PodcastEpisodeNotes.text("<p><a href=\"javascript:alert(1)\">Click here</a> and <a href=\"mailto:hello@example.com\">Email</a>.</p>"))
        #expect(text.contains("Click here"))
        #expect(text.contains("Email"))
        let attributed = PodcastEpisodeNotes.attributedText(text)
        #expect(String(attributed.characters) == text)
        #expect(linkedRuns(attributed).isEmpty)
    }

    @Test("safe destinations in literal markdown link only their visible URL")
    func safeMarkdownURL() {
        let text = "[Episode notes](https://example.com/notes)"
        let attributed = PodcastEpisodeNotes.attributedText(text)
        #expect(String(attributed.characters) == text)
        #expect(linkedRuns(attributed).allSatisfy { $0.text == "https://example.com/notes" })
        #expect(linkedRuns(attributed).contains { $0.url.absoluteString == "https://example.com/notes" })
        #expect(attributed.runs.allSatisfy { $0.inlinePresentationIntent == nil })
    }

    private func linkedRuns(_ text: AttributedString) -> [(text: String, url: URL)] {
        text.runs.compactMap { run in
            guard let url = run.link else { return nil }
            return (String(text[run.range].characters), url)
        }
    }
}

#if canImport(UIKit)
import SwiftUI
import UIKit
import Vision
import LaughTrackBridge

@Suite("Podcast episode notes layout", .serialized)
@MainActor
struct PodcastEpisodeNotesLayoutTests {
    @Test("notes disclose complete content and wrap web links at accessible sizes", arguments: [false, true])
    func notesPresentation(_ accessibility: Bool) async throws {
        let longText = "A conversation about writing jokes and finding your voice.\n\n"
            + String(repeating: "We discuss comedy, creativity, and performing on the road. ", count: 6)
            + "\n\nhttps://example.com/episodes/averylongunbrokensegmentthatmustwrapwithoutoverflowingthecard?source=episodenotes&language=english"
            + "\n\nFinal credits: thank you for listening."
        let profile = accessibility ? "accessibility" : "default"
        var collapsedHeight: CGFloat = 0
        var expandedHeight: CGFloat = 0
        for scenario in ["collapsed", "expanded", "short"] {
            let measured = EpisodeNotesCardMeasurement()
            let text = scenario == "short" ? "Recorded live in Brooklyn." : longText
            let host = HostedView(ScrollView {
                DetailTextCard(eyebrow: "Episode notes", title: "About this episode", text: text,
                    isCollapsible: true, detectsWebLinks: true, isExpanded: scenario == "expanded")
                    .background(GeometryReader { geometry in
                        Color.clear
                            .onAppear { measured.size = geometry.size }
                            .onChange(of: geometry.size) { measured.size = $0 }
                    })
                    .padding(16)
            }
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.dynamicTypeSize, accessibility ? .accessibility3 : .large)
            .preferredColorScheme(.dark), freshWindow: true, viewportSize: CGSize(width: 375, height: 812))
            await host.settle(iterations: 16)
            #expect(measured.size.width > 0)
            #expect(measured.size.width <= 343.5, "Notes must fit the 375-point viewport with 16-point side padding")
            let first = try capture(host, name: "\(profile)-\(scenario)-top")
            if scenario == "collapsed" {
                collapsedHeight = measured.size.height
                #expect(first.contains("show more"))
                #expect(!first.contains("final credits"))
            } else if scenario == "short" {
                #expect(first.contains("recorded live in brooklyn"))
                #expect(!first.contains("show more"))
                #expect(!first.contains("show less"))
            } else {
                expandedHeight = measured.size.height
                // Capture the middle as well as both ends for long-URL wrapping review.
                host.scrollDown(pages: 1)
                await host.settle(iterations: 8)
                _ = try capture(host, name: "\(profile)-expanded-middle")
                host.scrollDown(pages: 100)
                await host.settle(iterations: 8)
                let bottom = try capture(host, name: "\(profile)-expanded-bottom")
                #expect(bottom.contains("final credits"))
                #expect(bottom.contains("thank you for listening"))
                #expect(bottom.contains("show less"))
            }
        }
        #expect(expandedHeight > collapsedHeight, "Expanding must reveal the retained notes rather than replace or lose them")
    }

    private func capture(_ host: HostedView, name: String) throws -> String {
        let image = try host.snapshot()
        let output = FileManager.default.temporaryDirectory.appendingPathComponent("task4030-\(name).png")
        let png = try #require(image.pngData())
        try png.write(to: output)
        print("Episode notes capture: \(output.path)")
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = ["en-US"]
        request.usesLanguageCorrection = false
        let cgImage = try #require(image.cgImage)
        try VNImageRequestHandler(cgImage: cgImage, options: [:]).perform([request])
        return (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
            .joined(separator: " ").lowercased()
    }
}

@MainActor
private final class EpisodeNotesCardMeasurement {
    var size: CGSize = .zero
}

#endif
