import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct LaughTrackAtmosphereBackground: View {
    @Environment(\.appTheme) private var theme
    private let spotlightHue = Color(red: 1.0, green: 0.72, blue: 0.30)

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            laughTrack.colors.canvas

            RadialGradient(
                colors: [
                    spotlightHue.opacity(0.30),
                    laughTrack.colors.accentStrong.opacity(0.18),
                    laughTrack.colors.canvas.opacity(0.0),
                ],
                center: .topLeading,
                startRadius: 0,
                endRadius: 430
            )

            LinearGradient(
                colors: [
                    spotlightHue.opacity(0.22),
                    laughTrack.colors.heroEnd.opacity(0.20),
                    laughTrack.colors.accentMuted.opacity(0.10),
                    laughTrack.colors.canvas.opacity(0.0),
                ],
                startPoint: .topLeading,
                endPoint: UnitPoint(x: 0.72, y: 0.46)
            )

            RadialGradient(
                colors: [
                    laughTrack.colors.accentStrong.opacity(0.24),
                    laughTrack.colors.accentMuted.opacity(0.08),
                    laughTrack.colors.canvas.opacity(0.0),
                ],
                center: UnitPoint(x: 0.72, y: 0.08),
                startRadius: 18,
                endRadius: 300
            )

            RadialGradient(
                colors: [
                    Color(red: 0.34, green: 0.04, blue: 0.07).opacity(0.24),
                    laughTrack.colors.canvas.opacity(0.0),
                ],
                center: UnitPoint(x: 0.05, y: 0.56),
                startRadius: 36,
                endRadius: 360
            )
        }
    }
}

enum HomeDiscoverRailVariant {
    case spotlight
    case scheduleBoard
    case posterGrid
    case listeningRoom

    var topGlowAlignment: UnitPoint {
        switch self {
        case .spotlight:
            return UnitPoint(x: 0.5, y: 0.0)
        case .scheduleBoard:
            return UnitPoint(x: 0.14, y: 0.0)
        case .posterGrid:
            return UnitPoint(x: 0.78, y: 0.02)
        case .listeningRoom:
            return UnitPoint(x: 0.5, y: 0.12)
        }
    }

    var surfaceOpacity: Double {
        switch self {
        case .spotlight:
            return 0.70
        case .scheduleBoard:
            return 0.78
        case .posterGrid:
            return 0.74
        case .listeningRoom:
            return 0.70
        }
    }

    var glowOpacity: Double {
        switch self {
        case .spotlight:
            return 0.24
        case .scheduleBoard:
            return 0.16
        case .posterGrid:
            return 0.18
        case .listeningRoom:
            return 0.14
        }
    }
}

struct HomeDiscoverRailCard<Content: View>: View {
    let variant: HomeDiscoverRailVariant
    let eyebrow: String?
    let title: String?
    let subtitle: String?
    let accessibilityIdentifier: String?
    let actionTitle: String?
    let actionAccessibilityIdentifier: String?
    let action: (() -> Void)?
    @ViewBuilder let content: Content

    @Environment(\.appTheme) private var theme

    init(
        variant: HomeDiscoverRailVariant,
        eyebrow: String? = nil,
        title: String? = nil,
        subtitle: String? = nil,
        accessibilityIdentifier: String? = nil,
        actionTitle: String? = nil,
        actionAccessibilityIdentifier: String? = nil,
        action: (() -> Void)? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.variant = variant
        self.eyebrow = eyebrow
        self.title = title
        self.subtitle = subtitle
        self.accessibilityIdentifier = accessibilityIdentifier
        self.actionTitle = actionTitle
        self.actionAccessibilityIdentifier = actionAccessibilityIdentifier
        self.action = action
        self.content = content()
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.md) {
            if let title {
                HomeDiscoverSectionHeader(
                    eyebrow: eyebrow,
                    title: title,
                    subtitle: subtitle
                )
                .modifier(HomeRailAccessibilityIdentifierModifier(identifier: accessibilityIdentifier))
            }

            content

            if let actionTitle, let action {
                HomeDiscoverRailAction(
                    title: actionTitle,
                    accessibilityIdentifier: actionAccessibilityIdentifier,
                    action: action
                )
            }
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(railBackground)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.accentMuted.opacity(0.34), lineWidth: 1)
        )
        .overlay(alignment: .topLeading) {
            Capsule(style: .continuous)
                .fill(laughTrack.colors.accentStrong.opacity(0.72))
                .frame(width: 52, height: 2)
                .padding(.leading, laughTrack.browseDensity.compactCardPadding)
                .shadow(color: laughTrack.colors.accentStrong.opacity(0.44), radius: 8)
        }
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
        .modifier(HomeRailAccessibilityIdentifierModifier(
            identifier: title == nil ? accessibilityIdentifier : nil
        ))
    }

    private var railBackground: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            laughTrack.colors.surfaceElevated.opacity(variant.surfaceOpacity)

            RadialGradient(
                colors: [
                    laughTrack.colors.accent.opacity(variant.glowOpacity),
                    laughTrack.colors.accentMuted.opacity(variant.glowOpacity * 0.35),
                    laughTrack.colors.surface.opacity(0.0),
                ],
                center: variant.topGlowAlignment,
                startRadius: 12,
                endRadius: 240
            )

            LinearGradient(
                colors: [
                    Color.white.opacity(0.035),
                    Color.black.opacity(0.10),
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        }
    }
}

private struct HomeRailAccessibilityIdentifierModifier: ViewModifier {
    let identifier: String?

    func body(content: Content) -> some View {
        if let identifier {
            content.accessibilityIdentifier(identifier)
        } else {
            content
        }
    }
}

private struct HomeDiscoverSectionHeader: View {
    let eyebrow: String?
    let title: String
    let subtitle: String?

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: 7) {
            if let eyebrow {
                Text(eyebrow)
                    .font(.system(size: 10, weight: .heavy, design: .rounded))
                    .tracking(2.0)
                    .textCase(.uppercase)
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .lineLimit(1)
            }

            HStack(alignment: .firstTextBaseline, spacing: theme.spacing.sm) {
                Text(title)
                    .font(.system(size: 22, weight: .heavy, design: .rounded))
                    .tracking(0.3)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)

                Spacer(minLength: 0)

                HStack(spacing: 4) {
                    ForEach(0..<5, id: \.self) { index in
                        Circle()
                            .fill(laughTrack.colors.accentStrong.opacity(0.85 - Double(index) * 0.11))
                            .frame(width: 4, height: 4)
                            .shadow(color: laughTrack.colors.accentStrong.opacity(0.34), radius: 4)
                    }
                }
                .accessibilityHidden(true)
            }

            if let subtitle {
                Text(subtitle)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

private struct HomeDiscoverRailAction: View {
    let title: String
    let accessibilityIdentifier: String?
    let action: () -> Void

    var body: some View {
        LaughTrackButton(
            title,
            systemImage: "magnifyingglass",
            tone: .secondary,
            density: .compact,
            action: action
        )
        .modifier(HomeRailAccessibilityIdentifierModifier(
            identifier: accessibilityIdentifier
        ))
    }
}

struct HomeMarqueeStageBackground: View {
    var glowRadius: CGFloat = 140
    var glowOpacity: Double = 0.22

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            laughTrack.colors.heroStart

            RadialGradient(
                colors: [
                    laughTrack.colors.accent.opacity(glowOpacity),
                    laughTrack.colors.accent.opacity(0.0)
                ],
                center: .center,
                startRadius: 12,
                endRadius: glowRadius
            )
        }
        .mask(
            LinearGradient(
                stops: [
                    .init(color: .black.opacity(0), location: 0),
                    .init(color: .black.opacity(0.5), location: 0.06),
                    .init(color: .black, location: 0.16),
                    .init(color: .black, location: 0.84),
                    .init(color: .black.opacity(0.5), location: 0.94),
                    .init(color: .black.opacity(0), location: 1)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        )
    }
}

struct HomeBulbFrame: View {
    var width: CGFloat
    var height: CGFloat
    var cornerRadius: CGFloat
    var isCircle = false
    var lineWidth: CGFloat = 2
    var dash: [CGFloat] = [0.5, 6]
    var bulbColor: Color? = nil

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let resolvedBulbColor = bulbColor ?? laughTrack.colors.accentStrong
        let stroke = StrokeStyle(
            lineWidth: lineWidth,
            lineCap: .round,
            lineJoin: .round,
            dash: dash
        )

        Group {
            if isCircle {
                Circle()
                    .strokeBorder(resolvedBulbColor, style: stroke)
            } else {
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .strokeBorder(resolvedBulbColor, style: stroke)
            }
        }
        .frame(width: width, height: height)
        .shadow(color: resolvedBulbColor.opacity(0.70), radius: 4)
        .shadow(color: resolvedBulbColor.opacity(0.34), radius: 9)
    }
}
