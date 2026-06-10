import CoreText
import Foundation
import Testing
import UIKit
import LaughTrackBridge

@Suite("LaughTrackTheme")
struct LaughTrackThemeTests {

    @Test("semantic LaughTrack tokens are exposed through the bridge")
    func semanticTokensAreAvailable() {
        let theme = LaughTrackTheme()

        #expect(theme.laughTrack.spacing.heroPadding > theme.spacing.xl)
        #expect(theme.laughTrack.radius.heroPanel > theme.cornerRadius.lg)
        #expect(theme.laughTrackTokens.spacing.heroPadding == theme.laughTrack.spacing.heroPadding)
    }

    @Test("generic app theme groups stay aligned with semantic LaughTrack roles")
    func genericThemeMapsToSemanticRoles() {
        let theme = LaughTrackTheme()

        #expect(theme.spacing.section == theme.laughTrack.spacing.sectionGap)
        #expect(theme.cornerRadius.full == theme.laughTrack.radius.pill)
        #expect(theme.typography.button == theme.laughTrack.typography.action)
        #expect(theme.iconSizes.huge >= theme.iconSizes.lg)
    }

    @Test("browse tokens expose denser defaults without collapsing surfaces")
    func browseTokensExposeDenseSurfaceDefaults() {
        let theme = LaughTrackTheme()

        #expect(theme.laughTrack.browseDensity.compactCardPadding < theme.laughTrack.spacing.cardPadding)
        #expect(theme.laughTrack.browseDensity.resultRowMinHeight < 96)
        #expect(theme.laughTrack.colors.canvas != theme.laughTrack.colors.surfaceElevated)
        #expect(theme.laughTrackTokens.browseDensity.heroPadding == theme.laughTrack.browseDensity.heroPadding)
    }

    @Test("theme custom font tokens resolve to bundled font PostScript names")
    func themeCustomFontTokensResolveToBundledFonts() throws {
        let iosRoot = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let fontDirectory = iosRoot.appending(path: "Resources/Fonts", directoryHint: .isDirectory)
        let themeSourceURL = iosRoot.appending(path: "Sources/LaughTrackBridge/LaughTrackTheme.swift")

        let registeredPostScriptNames = try registerBundledFontFiles(in: fontDirectory)
        let themeFontNames = try customFontNames(in: themeSourceURL)

        #expect(!registeredPostScriptNames.isEmpty)
        #expect(!themeFontNames.isEmpty)

        for fontName in themeFontNames {
            #expect(
                registeredPostScriptNames.contains(fontName),
                "Theme font token '\(fontName)' does not match any bundled font PostScript name"
            )
            #expect(
                UIFont(name: fontName, size: 12) != nil,
                "Theme font token '\(fontName)' did not resolve via UIFont(name:size:)"
            )
        }
    }

    private func registerBundledFontFiles(in fontDirectory: URL) throws -> Set<String> {
        let fontURLs = try FileManager.default.contentsOfDirectory(
            at: fontDirectory,
            includingPropertiesForKeys: nil
        )
        .filter { $0.pathExtension.lowercased() == "ttf" }
        .sorted { $0.lastPathComponent < $1.lastPathComponent }

        var postScriptNames = Set<String>()

        for fontURL in fontURLs {
            let fontName = try postScriptName(for: fontURL)
            var registrationError: Unmanaged<CFError>?
            let registered = CTFontManagerRegisterFontsForURL(fontURL as CFURL, .process, &registrationError)

            #expect(
                registered || UIFont(name: fontName, size: 12) != nil,
                "Failed to register bundled font '\(fontURL.lastPathComponent)'"
            )

            postScriptNames.insert(fontName)
        }

        return postScriptNames
    }

    private func postScriptName(for fontURL: URL) throws -> String {
        guard
            let provider = CGDataProvider(url: fontURL as CFURL),
            let font = CGFont(provider),
            let postScriptName = font.postScriptName as String?
        else {
            throw FontTestError.unreadableFont(fontURL.path)
        }

        return postScriptName
    }

    private func customFontNames(in themeSourceURL: URL) throws -> [String] {
        let source = try String(contentsOf: themeSourceURL)
        let regex = try NSRegularExpression(pattern: #"\.custom\("([^"]+)",\s*size:"#)
        let matches = regex.matches(in: source, range: NSRange(source.startIndex..., in: source))

        return Set(matches.compactMap { match in
            guard let range = Range(match.range(at: 1), in: source) else {
                return nil
            }

            return String(source[range])
        }).sorted()
    }

    private enum FontTestError: Error {
        case unreadableFont(String)
    }
}
