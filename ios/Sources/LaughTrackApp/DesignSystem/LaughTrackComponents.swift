import SwiftUI
import LaughTrackBridge
import LaughTrackCore

enum LaughTrackButtonTone: Equatable {
    case primary
    case secondary
    case tertiary
    case destructive
}

enum LaughTrackButtonDensity: Equatable {
    case standard
    case compact
}

struct LaughTrackButton: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let systemImage: String?
    let tone: LaughTrackButtonTone
    let density: LaughTrackButtonDensity
    let fullWidth: Bool
    let action: () -> Void

    init(
        _ title: String,
        systemImage: String? = nil,
        tone: LaughTrackButtonTone = .primary,
        density: LaughTrackButtonDensity = .standard,
        fullWidth: Bool = true,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.systemImage = systemImage
        self.tone = tone
        self.density = density
        self.fullWidth = fullWidth
        self.action = action
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button(action: action) {
            HStack(spacing: theme.spacing.sm) {
                if let systemImage {
                    Image(systemName: systemImage)
                        .font(.system(size: theme.iconSizes.md, weight: .semibold))
                }

                Text(title)
                    .font(buttonFont)

                if tone == .tertiary {
                    Image(systemName: "arrow.right")
                        .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                }
            }
            .foregroundStyle(foregroundColor)
            .frame(maxWidth: fullWidth ? .infinity : nil)
            .padding(.horizontal, horizontalPadding)
            .padding(.vertical, verticalPadding)
            .background(background)
            .overlay(borderOverlay)
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous))
            .shadowStyle(componentShadowStyle)
        }
        .buttonStyle(.plain)
    }

    private var buttonFont: Font {
        let laughTrack = theme.laughTrackTokens

        switch density {
        case .standard:
            return laughTrack.typography.action
        case .compact:
            return laughTrack.typography.metadata
        }
    }

    private var horizontalPadding: CGFloat {
        switch density {
        case .standard:
            return theme.spacing.lg
        case .compact:
            return theme.laughTrackTokens.browseDensity.compactCardPadding
        }
    }

    private var verticalPadding: CGFloat {
        switch density {
        case .standard:
            return theme.spacing.md
        case .compact:
            return theme.spacing.sm
        }
    }

    private var foregroundColor: Color {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .primary:
            return laughTrack.colors.textInverse
        case .secondary, .tertiary:
            return laughTrack.colors.textPrimary
        case .destructive:
            return laughTrack.colors.danger
        }
    }

    @ViewBuilder
    private var background: some View {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .primary:
            laughTrack.colors.accent
        case .secondary:
            laughTrack.colors.surfaceElevated
        case .tertiary:
            laughTrack.colors.highlight.opacity(0.75)
        case .destructive:
            laughTrack.colors.danger.opacity(0.12)
        }
    }

    @ViewBuilder
    private var borderOverlay: some View {
        let laughTrack = theme.laughTrackTokens

        RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous)
            .stroke(borderColor, lineWidth: 1)
    }

    private var borderColor: Color {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .primary:
            return laughTrack.colors.accentStrong.opacity(0.2)
        case .secondary:
            return laughTrack.colors.borderSubtle
        case .tertiary:
            return laughTrack.colors.borderStrong.opacity(0.6)
        case .destructive:
            return laughTrack.colors.danger.opacity(0.3)
        }
    }

    private var componentShadowStyle: LaughTrackBridge.ShadowStyle {
        let laughTrack = theme.laughTrackTokens
        switch tone {
        case .primary:
            return laughTrack.shadows.floating
        case .secondary, .tertiary, .destructive:
            return laughTrack.shadows.card
        }
    }
}

enum LaughTrackCardTone {
    case standard
    case muted
    case accent
}

enum LaughTrackCardDensity: Equatable {
    case standard
    case compact
}

enum LaughTrackBadgeTone {
    case neutral
    case accent
    case highlight
    case warning
}

struct LaughTrackCard<Content: View>: View {
    @Environment(\.appTheme) private var theme

    let tone: LaughTrackCardTone
    let density: LaughTrackCardDensity
    let content: Content

    init(
        tone: LaughTrackCardTone = .standard,
        density: LaughTrackCardDensity = .standard,
        @ViewBuilder content: () -> Content
    ) {
        self.tone = tone
        self.density = density
        self.content = content()
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        content
            .padding(contentPadding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(background)
            .overlay(borderOverlay)
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
            .shadowStyle(componentShadowStyle)
    }

    private var contentPadding: CGFloat {
        switch density {
        case .standard:
            return theme.laughTrackTokens.spacing.cardPadding
        case .compact:
            return theme.laughTrackTokens.browseDensity.compactCardPadding
        }
    }

    @ViewBuilder
    private var background: some View {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .standard:
            laughTrack.colors.surfaceElevated
        case .muted:
            laughTrack.colors.surfaceMuted
        case .accent:
            laughTrack.gradients.heroWash
        }
    }

    @ViewBuilder
    private var borderOverlay: some View {
        let laughTrack = theme.laughTrackTokens

        RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
            .stroke(borderColor, lineWidth: 1)
    }

    private var borderColor: Color {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .standard:
            return laughTrack.colors.borderSubtle
        case .muted:
            return laughTrack.colors.borderStrong.opacity(0.55)
        case .accent:
            return laughTrack.colors.accentMuted.opacity(0.45)
        }
    }

    private var componentShadowStyle: LaughTrackBridge.ShadowStyle {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .accent:
            return laughTrack.shadows.hero
        case .standard, .muted:
            return laughTrack.shadows.card
        }
    }
}

struct LaughTrackBadge: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let systemImage: String?
    let tone: LaughTrackBadgeTone

    init(_ title: String, systemImage: String? = nil, tone: LaughTrackBadgeTone = .neutral) {
        self.title = title
        self.systemImage = systemImage
        self.tone = tone
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.xs) {
            if let systemImage {
                Image(systemName: systemImage)
                    .font(.system(size: theme.iconSizes.sm, weight: .semibold))
            }

            Text(title)
                .font(laughTrack.typography.metadata)
                .lineLimit(1)
        }
        .foregroundStyle(foregroundColor)
        .padding(.horizontal, theme.spacing.md)
        .padding(.vertical, theme.spacing.xs)
        .background(background)
        .overlay(
            Capsule(style: .continuous)
                .stroke(borderColor, lineWidth: 1)
        )
        .clipShape(Capsule(style: .continuous))
    }

    private var foregroundColor: Color {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .neutral:
            return laughTrack.colors.textPrimary
        case .accent:
            return laughTrack.colors.accentStrong
        case .highlight:
            return laughTrack.colors.textPrimary
        case .warning:
            return laughTrack.colors.danger
        }
    }

    private var background: Color {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .neutral:
            return laughTrack.colors.canvas
        case .accent:
            return laughTrack.colors.accentMuted.opacity(0.45)
        case .highlight:
            return laughTrack.colors.highlight.opacity(0.85)
        case .warning:
            return laughTrack.colors.danger.opacity(0.12)
        }
    }

    private var borderColor: Color {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .neutral:
            return laughTrack.colors.borderSubtle
        case .accent:
            return laughTrack.colors.accentStrong.opacity(0.35)
        case .highlight:
            return laughTrack.colors.borderStrong.opacity(0.5)
        case .warning:
            return laughTrack.colors.danger.opacity(0.3)
        }
    }
}

struct LaughTrackSectionHeader: View {
    @Environment(\.appTheme) private var theme

    enum Density: Equatable {
        case standard
        case compact
    }

    let eyebrow: String?
    let title: String
    let subtitle: String?
    let actionTitle: String?
    let action: (() -> Void)?
    let density: Density

    init(
        eyebrow: String? = nil,
        title: String,
        subtitle: String? = nil,
        actionTitle: String? = nil,
        action: (() -> Void)? = nil,
        density: Density = .standard
    ) {
        self.eyebrow = eyebrow
        self.title = title
        self.subtitle = subtitle
        self.actionTitle = actionTitle
        self.action = action
        self.density = density
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(alignment: .top, spacing: horizontalSpacing) {
            VStack(alignment: .leading, spacing: verticalSpacing) {
                if let eyebrow {
                    Text(eyebrow)
                        .font(laughTrack.typography.eyebrow)
                        .foregroundStyle(laughTrack.colors.accent)
                        .textCase(.uppercase)
                }

                Text(title)
                    .font(titleFont)
                    .foregroundStyle(laughTrack.colors.textPrimary)

                if let subtitle {
                    Text(subtitle)
                        .font(subtitleFont)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                }
            }

            Spacer(minLength: 0)

            if let actionTitle, let action {
                LaughTrackButton(
                    actionTitle,
                    systemImage: "arrow.up.right",
                    tone: .tertiary,
                    density: density == .compact ? .compact : .standard,
                    fullWidth: false,
                    action: action
                )
            }
        }
    }

    private var horizontalSpacing: CGFloat {
        switch density {
        case .standard:
            return theme.spacing.md
        case .compact:
            return theme.laughTrackTokens.browseDensity.rowGap
        }
    }

    private var verticalSpacing: CGFloat {
        switch density {
        case .standard:
            return theme.laughTrackTokens.spacing.tight
        case .compact:
            return theme.spacing.xxs
        }
    }

    private var titleFont: Font {
        let laughTrack = theme.laughTrackTokens
        switch density {
        case .standard:
            return laughTrack.typography.sectionTitle
        case .compact:
            return laughTrack.typography.cardTitle
        }
    }

    private var subtitleFont: Font {
        let laughTrack = theme.laughTrackTokens
        switch density {
        case .standard:
            return laughTrack.typography.body
        case .compact:
            return laughTrack.typography.metadata
        }
    }
}

struct LaughTrackLabeledField<Content: View>: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let detail: String?
    let content: Content

    init(
        title: String,
        detail: String? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.title = title
        self.detail = detail
        self.content = content()
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            HStack(alignment: .firstTextBaseline, spacing: theme.spacing.sm) {
                Text(title)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .textCase(.uppercase)

                Spacer(minLength: 0)

                if let detail {
                    Text(detail)
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.accent)
                }
            }

            content
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(theme.spacing.md)
                .background(laughTrack.colors.canvas)
                .overlay(
                    RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                        .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        }
    }
}

struct LaughTrackAvatar: View {
    @Environment(\.appTheme) private var theme

    enum Style {
        case initials(String)
        case symbol(String)
        case url(URL?, fallback: String)
    }

    let style: Style
    let size: CGFloat
    let highlighted: Bool

    init(style: Style, size: CGFloat = 56, highlighted: Bool = false) {
        self.style = style
        self.size = size
        self.highlighted = highlighted
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            Circle()
                .fill(highlighted ? laughTrack.gradients.accentWash : LinearGradient(colors: [
                    laughTrack.colors.highlight,
                    laughTrack.colors.surfaceElevated
                ], startPoint: .topLeading, endPoint: .bottomTrailing))

            Circle()
                .stroke(laughTrack.colors.borderStrong.opacity(highlighted ? 0.85 : 0.45), lineWidth: 1)

            avatarContent
        }
        .frame(width: size, height: size)
        .shadowStyle(highlighted ? laughTrack.shadows.floating : laughTrack.shadows.card)
    }

    @ViewBuilder
    private var avatarContent: some View {
        let laughTrack = theme.laughTrackTokens

        switch style {
        case .initials(let value):
            Text(value)
                .font(laughTrack.typography.cardTitle)
                .foregroundStyle(laughTrack.colors.textPrimary)
        case .symbol(let value):
            Image(systemName: value)
                .font(.system(size: size * 0.4, weight: .semibold))
                .foregroundStyle(laughTrack.colors.accentStrong)
        case .url(let url, let fallback):
            if let url {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFill()
                            .frame(width: size, height: size)
                            .clipShape(Circle())
                    case .empty, .failure:
                        Image(systemName: fallback)
                            .font(.system(size: size * 0.4, weight: .semibold))
                            .foregroundStyle(laughTrack.colors.accentStrong)
                    @unknown default:
                        Image(systemName: fallback)
                            .font(.system(size: size * 0.4, weight: .semibold))
                            .foregroundStyle(laughTrack.colors.accentStrong)
                    }
                }
            } else {
                Image(systemName: fallback)
                    .font(.system(size: size * 0.4, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
        }
    }
}

struct LaughTrackFavoriteButton: View {
    @Environment(\.appTheme) private var theme

    @Binding var isFavorite: Bool

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button {
            withAnimation(laughTrack.motion.tapFeedback) {
                isFavorite.toggle()
            }
        } label: {
            Image(systemName: isFavorite ? "heart.fill" : "heart")
                .font(.system(size: theme.iconSizes.md, weight: .semibold))
                .foregroundStyle(isFavorite ? laughTrack.colors.accentStrong : laughTrack.colors.textSecondary)
                .padding(theme.spacing.sm)
                .background(isFavorite ? laughTrack.colors.highlight : laughTrack.colors.surface)
                .overlay(
                    Circle()
                        .stroke(isFavorite ? laughTrack.colors.accentMuted : laughTrack.colors.borderSubtle, lineWidth: 1)
                )
                .clipShape(Circle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(isFavorite ? "Remove from favorites" : "Add to favorites")
    }
}

enum LaughTrackStateTone: Equatable {
    case loading
    case empty
    case error
}

struct LaughTrackStateView: View {
    @Environment(\.appTheme) private var theme

    let tone: LaughTrackStateTone
    let title: String
    let message: String
    let actionTitle: String?
    let action: (() -> Void)?

    init(
        tone: LaughTrackStateTone,
        title: String,
        message: String,
        actionTitle: String? = nil,
        action: (() -> Void)? = nil
    ) {
        self.tone = tone
        self.title = title
        self.message = message
        self.actionTitle = actionTitle
        self.action = action
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        LaughTrackCard(tone: .muted) {
            VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                indicator

                Text(title)
                    .font(laughTrack.typography.cardTitle)
                    .foregroundStyle(laughTrack.colors.textPrimary)

                Text(message)
                    .font(laughTrack.typography.body)
                    .foregroundStyle(laughTrack.colors.textSecondary)

                if let actionTitle, let action, tone != .loading {
                    LaughTrackButton(actionTitle, systemImage: tone == .error ? "arrow.clockwise" : "magnifyingglass", tone: .secondary, action: action)
                }
            }
        }
    }

    @ViewBuilder
    private var indicator: some View {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .loading:
            ProgressView()
                .progressViewStyle(.circular)
                .tint(laughTrack.colors.accent)
        case .empty:
            Image(systemName: "sparkles")
                .font(.system(size: theme.iconSizes.xl, weight: .semibold))
                .foregroundStyle(laughTrack.colors.accentStrong)
        case .error:
            Image(systemName: "wifi.exclamationmark")
                .font(.system(size: theme.iconSizes.xl, weight: .semibold))
                .foregroundStyle(laughTrack.colors.danger)
        }
    }
}

struct LaughTrackAuthMessageCard: View {
    let message: String

    var body: some View {
        LaughTrackStateView(
            tone: isCancelled ? .empty : .error,
            title: isCancelled ? "Sign-in cancelled" : "Couldn’t connect your account",
            message: message
        )
    }

    private var isCancelled: Bool {
        message.localizedCaseInsensitiveContains("cancelled")
    }
}

struct LaughTrackAuthProviderCard: View {
    @Environment(\.appTheme) private var theme

    let provider: AuthProvider
    let action: () -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button(action: action) {
            LaughTrackCard(tone: provider == .google ? .muted : .standard) {
                HStack(alignment: .center, spacing: laughTrack.spacing.itemGap) {
                    ZStack {
                        RoundedRectangle(cornerRadius: laughTrack.radius.chip, style: .continuous)
                            .fill(iconBackground)
                        Image(systemName: provider.symbolName)
                            .font(.system(size: theme.iconSizes.md, weight: .semibold))
                            .foregroundStyle(iconForeground)
                    }
                    .frame(width: 52, height: 52)

                    VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                        Text(provider.displayName)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.accent)
                            .textCase(.uppercase)

                        Text(provider.title)
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)

                        Text(provider.subtitle)
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer(minLength: 0)

                    Image(systemName: "arrow.up.right")
                        .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.textSecondary)
                }
            }
        }
        .buttonStyle(.plain)
    }

    private var iconBackground: Color {
        let laughTrack = theme.laughTrackTokens
        switch provider {
        case .apple:
            return laughTrack.colors.surfaceMuted
        case .google:
            return laughTrack.colors.highlight
        }
    }

    private var iconForeground: Color {
        let laughTrack = theme.laughTrackTokens
        switch provider {
        case .apple:
            return laughTrack.colors.textPrimary
        case .google:
            return laughTrack.colors.accentStrong
        }
    }
}

#if DEBUG
struct LaughTrackComponentGallery: View {
    @Environment(\.appTheme) private var theme
    @State private var favoriteSample = true

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: laughTrack.spacing.sectionGap) {
                LaughTrackSectionHeader(
                    eyebrow: "Preview",
                    title: "Shared component gallery",
                    subtitle: "Representative auth, browse, and detail pages built from the reusable LaughTrack iOS kit."
                )

                LaughTrackCard(tone: .accent) {
                    VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                        Text("LaughTrack iOS")
                            .font(laughTrack.typography.eyebrow)
                            .foregroundStyle(laughTrack.colors.textInverse.opacity(0.78))
                            .textCase(.uppercase)
                        Text("Reusable tokens, now with reusable surfaces.")
                            .font(laughTrack.typography.hero)
                            .foregroundStyle(laughTrack.colors.textInverse)
                        Text("Buttons, cards, section headers, favorites, and shared state views all come from the same native styling language.")
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textInverse.opacity(0.9))
                    }
                }

                LaughTrackSectionHeader(
                    eyebrow: "Browse",
                    title: "Comedian card",
                    subtitle: "Avatar, metadata, and a saved-state affordance that feels native on iOS."
                )

                LaughTrackCard {
                    HStack(alignment: .top, spacing: laughTrack.spacing.itemGap) {
                        LaughTrackAvatar(style: .initials("MN"), size: 64, highlighted: true)

                        VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                            Text("Mark Normand")
                                .font(laughTrack.typography.cardTitle)
                                .foregroundStyle(laughTrack.colors.textPrimary)
                            Text("Touring now")
                                .font(laughTrack.typography.metadata)
                                .foregroundStyle(laughTrack.colors.accent)
                                .textCase(.uppercase)
                            Text("New York, Austin, and Los Angeles dates are trending among your saved clubs.")
                                .font(laughTrack.typography.body)
                                .foregroundStyle(laughTrack.colors.textSecondary)
                        }

                        Spacer(minLength: 0)
                        LaughTrackFavoriteButton(isFavorite: $favoriteSample)
                    }
                }

                LaughTrackSectionHeader(
                    eyebrow: "States",
                    title: "Shared fallback patterns",
                    subtitle: "Loading, empty, and error treatments all pull from the same token-backed primitives."
                )

                VStack(spacing: laughTrack.spacing.itemGap) {
                    LaughTrackStateView(
                        tone: .loading,
                        title: "Fetching nearby shows",
                        message: "We’re checking your clubs, saved comedians, and tonight’s routes."
                    )
                    LaughTrackStateView(
                        tone: .empty,
                        title: "No matches yet",
                        message: "Try broadening the date range or removing the saved-only filter.",
                        actionTitle: "Browse all shows"
                    ) {}
                    LaughTrackStateView(
                        tone: .error,
                        title: "Couldn’t refresh favorites",
                        message: "Your saved comedian list is still available offline, but the latest sync did not finish.",
                        actionTitle: "Try again"
                    ) {}
                }
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.vertical, laughTrack.spacing.heroPadding)
        }
        .background(theme.laughTrackTokens.colors.canvas)
    }
}

struct LaughTrackComponentGallery_Previews: PreviewProvider {
    static var previews: some View {
        NavigationStack {
            LaughTrackComponentGallery()
                .environment(\.appTheme, LaughTrackTheme())
        }
    }
}
#endif
