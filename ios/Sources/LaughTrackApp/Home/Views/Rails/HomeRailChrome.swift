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
        Group {
            switch variant {
            case .spotlight:
                featuredRailContent
            case .scheduleBoard, .posterGrid, .listeningRoom:
                railContent
            }
        }
        .modifier(HomeRailAccessibilityIdentifierModifier(
            identifier: title == nil ? accessibilityIdentifier : nil
        ))
    }

    private var railContent: some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: theme.spacing.md) {
            if let title {
                HomeDiscoverSectionHeader(
                    eyebrow: eyebrow,
                    title: title,
                    subtitle: subtitle,
                    accessibilityIdentifier: accessibilityIdentifier,
                    actionTitle: actionTitle,
                    actionAccessibilityIdentifier: actionAccessibilityIdentifier,
                    action: action
                )
            } else if let actionTitle, let action {
                HomeDiscoverRailAction(
                    title: actionTitle,
                    sectionTitle: nil,
                    accessibilityIdentifier: actionAccessibilityIdentifier,
                    action: action
                )
            }

            content
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
    }

    private var featuredRailContent: some View {
        let laughTrack = theme.laughTrackTokens

        return railContent
            .background(featuredRailBackground)
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
    }

    private var featuredRailBackground: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            laughTrack.colors.surfaceElevated.opacity(0.70)

            RadialGradient(
                colors: [
                    laughTrack.colors.accent.opacity(0.24),
                    laughTrack.colors.accentMuted.opacity(0.24 * 0.35),
                    laughTrack.colors.surface.opacity(0.0),
                ],
                center: UnitPoint(x: 0.5, y: 0.0),
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
    let accessibilityIdentifier: String?
    let actionTitle: String?
    let actionAccessibilityIdentifier: String?
    let action: (() -> Void)?

    @Environment(\.appTheme) private var theme
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @ScaledMetric(relativeTo: .title2) private var titleSize: CGFloat = 22
    @ScaledMetric(relativeTo: .caption2) private var eyebrowSize: CGFloat = 10

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: 7) {
            if let eyebrow {
                Text(eyebrow)
                    .font(.system(size: eyebrowSize, weight: .heavy, design: .rounded))
                    .tracking(2.0)
                    .textCase(.uppercase)
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if dynamicTypeSize.isAccessibilitySize {
                VStack(alignment: .leading, spacing: 4) {
                    heading
                    headerAction
                }
            } else {
                HStack(alignment: .firstTextBaseline, spacing: theme.spacing.sm) {
                    heading
                    Spacer(minLength: 0)
                    headerAction
                        .fixedSize(horizontal: true, vertical: false)
                }
            }

            if let subtitle {
                Text(subtitle)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var heading: some View {
        Text(title)
            .font(.system(size: titleSize, weight: .heavy, design: .rounded))
            .tracking(0.3)
            .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
            .fixedSize(horizontal: false, vertical: true)
            .accessibilityAddTraits(.isHeader)
            .modifier(HomeRailAccessibilityIdentifierModifier(identifier: accessibilityIdentifier))
    }

    @ViewBuilder
    private var headerAction: some View {
        if let actionTitle, let action {
            HomeDiscoverRailAction(
                title: actionTitle,
                sectionTitle: title,
                accessibilityIdentifier: actionAccessibilityIdentifier,
                action: action
            )
        }
    }
}

private struct HomeDiscoverRailAction: View {
    let title: String
    let sectionTitle: String?
    let accessibilityIdentifier: String?
    let action: () -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        Button(action: action) {
            HStack(alignment: .firstTextBaseline, spacing: 5) {
                Text(title)
                    .fixedSize(horizontal: false, vertical: true)
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .accessibilityHidden(true)
            }
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(theme.laughTrackTokens.colors.accentStrong)
            .frame(minWidth: 44, minHeight: 44, alignment: .leading)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(sectionTitle.map { "\(title), \($0)" } ?? title)
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
