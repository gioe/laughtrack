#!/usr/bin/env swift
// Regenerates LaunchLogo PDFs into Assets.xcassets/LaunchLogo.imageset/.
//
// Bakes the rounded-design "LaughTrack" wordmark into the splash asset so
// the launch screen does not depend on storyboard SF Pro Rounded font
// resolution (unreliable on cold start). Also masks the AppIcon with the
// iOS squircle so the splash icon matches the home-screen treatment.
//
// Run from repo root: swift ios/bin/generate-launch-logo.swift

import AppKit
import CoreGraphics
import Foundation

let scriptURL = URL(fileURLWithPath: CommandLine.arguments[0])
let repoRoot = scriptURL
    .deletingLastPathComponent()  // bin/
    .deletingLastPathComponent()  // ios/
    .deletingLastPathComponent()  // <repo>

let iconURL = repoRoot.appendingPathComponent(
    "ios/Resources/Assets.xcassets/AppIcon.appiconset/Icon-App-1024x1024@1x.png"
)
let outDir = repoRoot.appendingPathComponent("ios/Resources/Assets.xcassets/LaunchLogo.imageset")

guard let icon = NSImage(contentsOf: iconURL),
      let iconCG = icon.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fputs("error: could not load \(iconURL.path)\n", stderr)
    exit(1)
}

try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)

func roundedHeavyFont(size: CGFloat) -> NSFont {
    let base = NSFont.systemFont(ofSize: size, weight: .heavy)
    guard let descriptor = base.fontDescriptor.withDesign(.rounded),
          let rounded = NSFont(descriptor: descriptor, size: size) else {
        fputs("warning: rounded design unavailable, falling back to system heavy\n", stderr)
        return base
    }
    return rounded
}

func renderPDF(to outURL: URL, wordmarkColor: NSColor) {
    let iconSize: CGFloat = 132
    let textGap: CGFloat = 18
    let pad: CGFloat = 12
    let fontSize: CGFloat = 56

    let attrs: [NSAttributedString.Key: Any] = [
        .font: roundedHeavyFont(size: fontSize),
        .foregroundColor: wordmarkColor,
    ]
    let attributed = NSAttributedString(string: "LaughTrack", attributes: attrs)
    let textSize = attributed.size()
    let textW = ceil(textSize.width)
    let textH = ceil(textSize.height)

    let canvasW = ceil(max(iconSize, textW) + pad * 2)
    let canvasH = ceil(iconSize + textGap + textH + pad * 2)

    var mediaBox = CGRect(x: 0, y: 0, width: canvasW, height: canvasH)
    guard let ctx = CGContext(outURL as CFURL, mediaBox: &mediaBox, nil) else {
        fputs("error: could not create PDF context at \(outURL.path)\n", stderr)
        exit(1)
    }
    ctx.beginPDFPage(nil)

    // Wordmark — PDF coords have origin at bottom-left, so wordmark sits at the bottom.
    let nsCtx = NSGraphicsContext(cgContext: ctx, flipped: false)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = nsCtx
    let textX = (canvasW - textW) / 2
    let textY = pad
    attributed.draw(at: CGPoint(x: textX, y: textY))
    NSGraphicsContext.restoreGraphicsState()

    // Icon above the wordmark, masked with the iOS app-icon squircle (~22.37% radius).
    let iconX = (canvasW - iconSize) / 2
    let iconY = pad + textH + textGap
    let iconRect = CGRect(x: iconX, y: iconY, width: iconSize, height: iconSize)
    ctx.saveGState()
    let cornerRadius = iconSize * 0.2237
    let path = CGPath(
        roundedRect: iconRect,
        cornerWidth: cornerRadius,
        cornerHeight: cornerRadius,
        transform: nil
    )
    ctx.addPath(path)
    ctx.clip()
    ctx.draw(iconCG, in: iconRect)
    ctx.restoreGState()

    ctx.endPDFPage()
    ctx.closePDF()
    print("wrote \(outURL.path) (\(Int(canvasW))x\(Int(canvasH)))")
}

// Brand-accent values mirror LaughTrackTheme.swift accent (light) / accentStrong-equivalent (dark).
let lightCopper = NSColor(srgbRed: 0xB8 / 255.0, green: 0x73 / 255.0, blue: 0x33 / 255.0, alpha: 1.0)
let darkCopper = NSColor(srgbRed: 0xCD / 255.0, green: 0x8B / 255.0, blue: 0x52 / 255.0, alpha: 1.0)

renderPDF(to: outDir.appendingPathComponent("LaunchLogo.pdf"), wordmarkColor: lightCopper)
renderPDF(to: outDir.appendingPathComponent("LaunchLogo-Dark.pdf"), wordmarkColor: darkCopper)
