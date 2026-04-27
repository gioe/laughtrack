#!/usr/bin/env swift
// Regenerates LaunchLogo PNGs into Assets.xcassets/LaunchLogo.imageset/.
//
// Bakes the rounded-design "LaughTrack" wordmark into the splash asset so
// the launch screen does not depend on storyboard SF Pro Rounded font
// resolution (unreliable on cold start). The AppIcon is squircle-masked
// so the splash icon matches the home-screen treatment.
//
// PNG (not PDF) renditions are emitted because the launch-screen render
// pipeline does not reliably honor vector PDF assets — the prior version
// shipped a vector PDF that compiled into Assets.car correctly but did not
// render on cold launch. PNGs at @1x/@2x/@3x render reliably across iOS
// versions and devices.
//
// Run from repo root: swift ios/bin/generate-launch-logo.swift
//
// Important: this script writes PNG files only — Contents.json is hand-edited.
// If you add or rename a -Dark variant here, also update
// LaunchLogo.imageset/Contents.json with a matching
// `appearances: [{appearance: luminosity, value: dark}]` entry, otherwise the
// PNG ships in the imageset but iOS never picks it up at cold launch. See
// ios/CLAUDE.md "Launch Screen Iteration" for the wider gotcha.

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

// Logical layout — same for every scale; only the bitmap pixel density changes.
let iconSize: CGFloat = 132
let textGap: CGFloat = 18
let pad: CGFloat = 12
let fontSize: CGFloat = 56

func textSize() -> CGSize {
    let attrs: [NSAttributedString.Key: Any] = [.font: roundedHeavyFont(size: fontSize)]
    return NSAttributedString(string: "LaughTrack", attributes: attrs).size()
}

let _txt = textSize()
let canvasW = ceil(max(iconSize, _txt.width) + pad * 2)
let canvasH = ceil(iconSize + textGap + ceil(_txt.height) + pad * 2)

func renderPNG(to outURL: URL, scale: CGFloat, wordmarkColor: NSColor) {
    let pxW = Int(canvasW * scale)
    let pxH = Int(canvasH * scale)
    let cs = CGColorSpaceCreateDeviceRGB()
    guard let ctx = CGContext(
        data: nil,
        width: pxW,
        height: pxH,
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: cs,
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else {
        fputs("error: could not create bitmap context for \(outURL.path)\n", stderr)
        exit(1)
    }
    ctx.scaleBy(x: scale, y: scale)

    // Wordmark — bottom (CG coords have origin at bottom-left).
    let attrs: [NSAttributedString.Key: Any] = [
        .font: roundedHeavyFont(size: fontSize),
        .foregroundColor: wordmarkColor,
    ]
    let attributed = NSAttributedString(string: "LaughTrack", attributes: attrs)
    let tSize = attributed.size()
    let textX = (canvasW - tSize.width) / 2
    let textY = pad
    let nsCtx = NSGraphicsContext(cgContext: ctx, flipped: false)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = nsCtx
    attributed.draw(at: CGPoint(x: textX, y: textY))
    NSGraphicsContext.restoreGraphicsState()

    // Icon — squircle-masked, centered above wordmark.
    let iconX = (canvasW - iconSize) / 2
    let iconY = pad + ceil(tSize.height) + textGap
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

    guard let cgImage = ctx.makeImage() else {
        fputs("error: could not finalize image at \(outURL.path)\n", stderr)
        exit(1)
    }
    let bitmap = NSBitmapImageRep(cgImage: cgImage)
    guard let png = bitmap.representation(using: .png, properties: [:]) else {
        fputs("error: png encoding failed for \(outURL.path)\n", stderr)
        exit(1)
    }
    try! png.write(to: outURL)
    print("wrote \(outURL.lastPathComponent) (\(pxW)x\(pxH))")
}

// Brand-accent values mirror LaughTrackTheme.swift accent (light) / accent dark.
let lightCopper = NSColor(srgbRed: 0xB8 / 255.0, green: 0x73 / 255.0, blue: 0x33 / 255.0, alpha: 1.0)
let darkCopper = NSColor(srgbRed: 0xCD / 255.0, green: 0x8B / 255.0, blue: 0x52 / 255.0, alpha: 1.0)

// Light variant
renderPNG(to: outDir.appendingPathComponent("LaunchLogo.png"), scale: 1, wordmarkColor: lightCopper)
renderPNG(to: outDir.appendingPathComponent("LaunchLogo@2x.png"), scale: 2, wordmarkColor: lightCopper)
renderPNG(to: outDir.appendingPathComponent("LaunchLogo@3x.png"), scale: 3, wordmarkColor: lightCopper)

// Dark variant
renderPNG(to: outDir.appendingPathComponent("LaunchLogo-Dark.png"), scale: 1, wordmarkColor: darkCopper)
renderPNG(to: outDir.appendingPathComponent("LaunchLogo-Dark@2x.png"), scale: 2, wordmarkColor: darkCopper)
renderPNG(to: outDir.appendingPathComponent("LaunchLogo-Dark@3x.png"), scale: 3, wordmarkColor: darkCopper)

print("canvas: \(Int(canvasW))x\(Int(canvasH)) pt")
