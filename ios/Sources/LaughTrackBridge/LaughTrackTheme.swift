import SharedKit
import SwiftUI

public struct LaughTrackSemanticColorTokens {
    public let canvas: Color
    public let surface: Color
    public let surfaceMuted: Color
    public let surfaceElevated: Color
    public let borderSubtle: Color
    public let borderStrong: Color
    public let textPrimary: Color
    public let textSecondary: Color
    public let textInverse: Color
    public let accent: Color
    public let accentStrong: Color
    public let accentMuted: Color
    public let heroStart: Color
    public let heroEnd: Color
    public let highlight: Color
    public let success: Color
    public let warning: Color
    public let danger: Color

    public init(
        canvas: Color,
        surface: Color,
        surfaceMuted: Color,
        surfaceElevated: Color,
        borderSubtle: Color,
        borderStrong: Color,
        textPrimary: Color,
        textSecondary: Color,
        textInverse: Color,
        accent: Color,
        accentStrong: Color,
        accentMuted: Color,
        heroStart: Color,
        heroEnd: Color,
        highlight: Color,
        success: Color,
        warning: Color,
        danger: Color
    ) {
        self.canvas = canvas
        self.surface = surface
        self.surfaceMuted = surfaceMuted
        self.surfaceElevated = surfaceElevated
        self.borderSubtle = borderSubtle
        self.borderStrong = borderStrong
        self.textPrimary = textPrimary
        self.textSecondary = textSecondary
        self.textInverse = textInverse
        self.accent = accent
        self.accentStrong = accentStrong
        self.accentMuted = accentMuted
        self.heroStart = heroStart
        self.heroEnd = heroEnd
        self.highlight = highlight
        self.success = success
        self.warning = warning
        self.danger = danger
    }
}

public struct LaughTrackSemanticTypographyTokens {
    public let hero: Font
    public let screenTitle: Font
    public let sectionTitle: Font
    public let cardTitle: Font
    public let body: Font
    public let bodyEmphasis: Font
    public let metadata: Font
    public let eyebrow: Font
    public let action: Font
    public let numericHighlight: Font

    public init(
        hero: Font,
        screenTitle: Font,
        sectionTitle: Font,
        cardTitle: Font,
        body: Font,
        bodyEmphasis: Font,
        metadata: Font,
        eyebrow: Font,
        action: Font,
        numericHighlight: Font
    ) {
        self.hero = hero
        self.screenTitle = screenTitle
        self.sectionTitle = sectionTitle
        self.cardTitle = cardTitle
        self.body = body
        self.bodyEmphasis = bodyEmphasis
        self.metadata = metadata
        self.eyebrow = eyebrow
        self.action = action
        self.numericHighlight = numericHighlight
    }
}

public struct LaughTrackSemanticSpacingTokens {
    public let tight: CGFloat
    public let itemGap: CGFloat
    public let clusterGap: CGFloat
    public let cardPadding: CGFloat
    public let sectionGap: CGFloat
    public let heroPadding: CGFloat

    public init(
        tight: CGFloat,
        itemGap: CGFloat,
        clusterGap: CGFloat,
        cardPadding: CGFloat,
        sectionGap: CGFloat,
        heroPadding: CGFloat
    ) {
        self.tight = tight
        self.itemGap = itemGap
        self.clusterGap = clusterGap
        self.cardPadding = cardPadding
        self.sectionGap = sectionGap
        self.heroPadding = heroPadding
    }
}

public struct LaughTrackSemanticRadiusTokens {
    public let chip: CGFloat
    public let card: CGFloat
    public let heroPanel: CGFloat
    public let pill: CGFloat

    public init(chip: CGFloat, card: CGFloat, heroPanel: CGFloat, pill: CGFloat) {
        self.chip = chip
        self.card = card
        self.heroPanel = heroPanel
        self.pill = pill
    }
}

public struct LaughTrackSemanticShadowTokens {
    public let card: ShadowStyle
    public let hero: ShadowStyle
    public let floating: ShadowStyle

    public init(card: ShadowStyle, hero: ShadowStyle, floating: ShadowStyle) {
        self.card = card
        self.hero = hero
        self.floating = floating
    }
}

public struct LaughTrackSemanticMotionTokens {
    public let tapFeedback: Animation
    public let contentEntrance: Animation
    public let emphasis: Animation

    public init(tapFeedback: Animation, contentEntrance: Animation, emphasis: Animation) {
        self.tapFeedback = tapFeedback
        self.contentEntrance = contentEntrance
        self.emphasis = emphasis
    }
}

public struct LaughTrackSemanticGradientTokens {
    public let heroWash: LinearGradient
    public let accentWash: LinearGradient

    public init(heroWash: LinearGradient, accentWash: LinearGradient) {
        self.heroWash = heroWash
        self.accentWash = accentWash
    }
}

public struct LaughTrackSemanticTokens {
    public let colors: LaughTrackSemanticColorTokens
    public let typography: LaughTrackSemanticTypographyTokens
    public let spacing: LaughTrackSemanticSpacingTokens
    public let radius: LaughTrackSemanticRadiusTokens
    public let shadows: LaughTrackSemanticShadowTokens
    public let motion: LaughTrackSemanticMotionTokens
    public let gradients: LaughTrackSemanticGradientTokens

    public init(
        colors: LaughTrackSemanticColorTokens,
        typography: LaughTrackSemanticTypographyTokens,
        spacing: LaughTrackSemanticSpacingTokens,
        radius: LaughTrackSemanticRadiusTokens,
        shadows: LaughTrackSemanticShadowTokens,
        motion: LaughTrackSemanticMotionTokens,
        gradients: LaughTrackSemanticGradientTokens
    ) {
        self.colors = colors
        self.typography = typography
        self.spacing = spacing
        self.radius = radius
        self.shadows = shadows
        self.motion = motion
        self.gradients = gradients
    }
}

public struct LaughTrackTheme: AppThemeProtocol {
    public let laughTrack: LaughTrackSemanticTokens

    public init() {
        let semanticColors = LaughTrackSemanticColorTokens(
            canvas: Color(light: Color(hex: "#FAF6E0") ?? .white, dark: Color(hex: "#1F1713") ?? .black),
            surface: Color(light: Color(hex: "#FFFDF7") ?? .white, dark: Color(hex: "#2B211C") ?? .black),
            surfaceMuted: Color(light: Color(hex: "#F5E6D3") ?? .white, dark: Color(hex: "#3B2A22") ?? .black),
            surfaceElevated: Color(light: Color(hex: "#FFFFFF") ?? .white, dark: Color(hex: "#342720") ?? .black),
            borderSubtle: Color(light: Color(hex: "#E8D7C5") ?? .gray, dark: Color(hex: "#4C392F") ?? .gray),
            borderStrong: Color(light: Color(hex: "#D5B79A") ?? .gray, dark: Color(hex: "#6E523F") ?? .gray),
            textPrimary: Color(light: Color(hex: "#361E14") ?? .black, dark: Color(hex: "#FAF1E8") ?? .white),
            textSecondary: Color(light: Color(hex: "#6C5648") ?? .gray, dark: Color(hex: "#D7C5B7") ?? .gray),
            textInverse: Color(light: .white, dark: Color(hex: "#FFF8F2") ?? .white),
            accent: Color(light: Color(hex: "#B87333") ?? .orange, dark: Color(hex: "#CD8B52") ?? .orange),
            accentStrong: Color(light: Color(hex: "#A96030") ?? .orange, dark: Color(hex: "#B87333") ?? .orange),
            accentMuted: Color(light: Color(hex: "#F2D6B8") ?? .orange, dark: Color(hex: "#6C4527") ?? .orange),
            heroStart: Color(light: Color(hex: "#361E14") ?? .black, dark: Color(hex: "#231713") ?? .black),
            heroEnd: Color(light: Color(hex: "#B87333") ?? .orange, dark: Color(hex: "#8D5628") ?? .orange),
            highlight: Color(light: Color(hex: "#F7E7CE") ?? .yellow, dark: Color(hex: "#5F472F") ?? .yellow),
            success: ColorPalette.successText,
            warning: ColorPalette.warningText,
            danger: ColorPalette.errorText
        )

        let semanticTypography = LaughTrackSemanticTypographyTokens(
            hero: .system(size: 34, weight: .heavy, design: .rounded),
            screenTitle: .system(size: 28, weight: .bold, design: .rounded),
            sectionTitle: .system(size: 22, weight: .bold, design: .rounded),
            cardTitle: .system(size: 20, weight: .semibold, design: .rounded),
            body: .system(size: 17, weight: .regular, design: .default),
            bodyEmphasis: .system(size: 17, weight: .medium, design: .default),
            metadata: .system(size: 13, weight: .medium, design: .default),
            eyebrow: .system(size: 12, weight: .semibold, design: .rounded),
            action: .system(size: 16, weight: .semibold, design: .rounded),
            numericHighlight: .system(size: 26, weight: .bold, design: .rounded)
        )

        let semanticSpacing = LaughTrackSemanticSpacingTokens(
            tight: DesignSystem.Spacing.xs,
            itemGap: DesignSystem.Spacing.sm,
            clusterGap: DesignSystem.Spacing.lg,
            cardPadding: DesignSystem.Spacing.xl,
            sectionGap: DesignSystem.Spacing.xxxl,
            heroPadding: 28
        )

        let semanticRadius = LaughTrackSemanticRadiusTokens(
            chip: DesignSystem.CornerRadius.full,
            card: DesignSystem.CornerRadius.lg,
            heroPanel: 28,
            pill: DesignSystem.CornerRadius.full
        )

        let semanticShadows = LaughTrackSemanticShadowTokens(
            card: ShadowStyle(
                color: Color.black.opacity(0.08),
                radius: 10,
                x: 0,
                y: 4
            ),
            hero: ShadowStyle(
                color: Color.black.opacity(0.18),
                radius: 18,
                x: 0,
                y: 10
            ),
            floating: ShadowStyle(
                color: Color.black.opacity(0.12),
                radius: 14,
                x: 0,
                y: 6
            )
        )

        let semanticMotion = LaughTrackSemanticMotionTokens(
            tapFeedback: .spring(response: 0.28, dampingFraction: 0.82),
            contentEntrance: .spring(response: 0.46, dampingFraction: 0.86),
            emphasis: .spring(response: 0.62, dampingFraction: 0.74)
        )

        let semanticGradients = LaughTrackSemanticGradientTokens(
            heroWash: LinearGradient(
                colors: [semanticColors.heroStart, semanticColors.heroEnd],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            accentWash: LinearGradient(
                colors: [semanticColors.highlight, semanticColors.accentMuted],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )

        self.laughTrack = LaughTrackSemanticTokens(
            colors: semanticColors,
            typography: semanticTypography,
            spacing: semanticSpacing,
            radius: semanticRadius,
            shadows: semanticShadows,
            motion: semanticMotion,
            gradients: semanticGradients
        )
    }

    public var colors: ColorTokens {
        ColorTokens(
            primary: laughTrack.colors.accent,
            secondary: laughTrack.colors.textPrimary,
            success: laughTrack.colors.success,
            warning: laughTrack.colors.warning,
            error: laughTrack.colors.danger,
            info: laughTrack.colors.accentStrong,
            successText: laughTrack.colors.success,
            warningText: laughTrack.colors.warning,
            errorText: laughTrack.colors.danger,
            infoText: laughTrack.colors.accentStrong,
            textPrimary: laughTrack.colors.textPrimary,
            textSecondary: laughTrack.colors.textSecondary,
            textTertiary: laughTrack.colors.textSecondary.opacity(0.72),
            background: laughTrack.colors.canvas,
            backgroundSecondary: laughTrack.colors.surface,
            backgroundTertiary: laughTrack.colors.surfaceMuted,
            backgroundGrouped: laughTrack.colors.canvas,
            statBlue: laughTrack.colors.accentStrong,
            statGreen: laughTrack.colors.success,
            statPurple: laughTrack.colors.heroStart,
            statOrange: laughTrack.colors.accent,
            textOnPrimary: laughTrack.colors.textInverse,
            scrim: Color.black.opacity(0.42)
        )
    }

    public var typography: TypographyTokens {
        TypographyTokens(
            h1: laughTrack.typography.hero,
            h2: laughTrack.typography.screenTitle,
            h3: laughTrack.typography.sectionTitle,
            h4: laughTrack.typography.cardTitle,
            bodyLarge: laughTrack.typography.body,
            bodyMedium: laughTrack.typography.body,
            bodySmall: laughTrack.typography.metadata,
            labelLarge: laughTrack.typography.bodyEmphasis,
            labelMedium: laughTrack.typography.action,
            labelSmall: laughTrack.typography.eyebrow,
            captionLarge: laughTrack.typography.metadata,
            captionMedium: laughTrack.typography.metadata,
            captionSmall: laughTrack.typography.metadata,
            statValue: laughTrack.typography.numericHighlight,
            button: laughTrack.typography.action
        )
    }

    public var spacing: SpacingTokens {
        SpacingTokens(
            xs: laughTrack.spacing.tight,
            sm: laughTrack.spacing.itemGap,
            md: DesignSystem.Spacing.md,
            lg: laughTrack.spacing.clusterGap,
            xl: laughTrack.spacing.cardPadding,
            xxl: DesignSystem.Spacing.xxl,
            xxxl: laughTrack.spacing.sectionGap,
            huge: laughTrack.spacing.heroPadding,
            section: laughTrack.spacing.sectionGap
        )
    }

    public var cornerRadius: CornerRadiusTokens {
        CornerRadiusTokens(
            sm: DesignSystem.CornerRadius.sm,
            md: DesignSystem.CornerRadius.md,
            lg: laughTrack.radius.card,
            xl: laughTrack.radius.heroPanel,
            full: laughTrack.radius.pill
        )
    }

    public var shadows: ShadowTokens {
        ShadowTokens(
            sm: laughTrack.shadows.card,
            md: laughTrack.shadows.floating,
            lg: laughTrack.shadows.hero
        )
    }

    public var iconSizes: IconSizeTokens {
        IconSizeTokens(
            sm: DesignSystem.IconSize.sm,
            md: DesignSystem.IconSize.md,
            lg: DesignSystem.IconSize.lg,
            xl: DesignSystem.IconSize.xl,
            huge: DesignSystem.IconSize.huge
        )
    }

    public var animations: AnimationTokens {
        AnimationTokens(
            quick: laughTrack.motion.tapFeedback,
            standard: laughTrack.motion.contentEntrance,
            smooth: laughTrack.motion.emphasis,
            bouncy: laughTrack.motion.emphasis
        )
    }

    public var gradients: GradientTokens {
        GradientTokens(
            scoreGradient: laughTrack.gradients.accentWash,
            trophyGradient: laughTrack.gradients.heroWash
        )
    }
}

public extension AppThemeProtocol {
    var laughTrackTokens: LaughTrackSemanticTokens {
        if let laughTrackTheme = self as? LaughTrackTheme {
            return laughTrackTheme.laughTrack
        }

        return LaughTrackTheme().laughTrack
    }
}
