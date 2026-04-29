import SwiftUI
import LaughTrackBridge

enum LaughTrackBrowseChipTone: Equatable {
    case neutral
    case accent
    case selected
}

struct LaughTrackHeroModule: View {
    @Environment(\.appTheme) private var theme

    let eyebrow: String?
    let title: String
    let subtitle: String?
    let ctaTitle: String?
    let action: (() -> Void)?

    init(
        eyebrow: String? = nil,
        title: String,
        subtitle: String? = nil,
        ctaTitle: String? = nil,
        action: (() -> Void)? = nil
    ) {
        self.eyebrow = eyebrow
        self.title = title
        self.subtitle = subtitle
        self.ctaTitle = ctaTitle
        self.action = action
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let browseDensity = laughTrack.browseDensity

        VStack(alignment: .leading, spacing: browseDensity.rowGap) {
            if let eyebrow {
                Text(eyebrow)
                    .font(laughTrack.typography.eyebrow)
                    .foregroundStyle(laughTrack.colors.textInverse.opacity(0.76))
                    .textCase(.uppercase)
            }

            Text(title)
                .font(laughTrack.typography.screenTitle)
                .foregroundStyle(laughTrack.colors.textInverse)
                .fixedSize(horizontal: false, vertical: true)

            if let subtitle {
                Text(subtitle)
                    .font(laughTrack.typography.body)
                    .foregroundStyle(laughTrack.colors.textInverse.opacity(0.88))
                    .fixedSize(horizontal: false, vertical: true)
            }

            if let ctaTitle {
                heroCTA(title: ctaTitle)
            }
        }
        .padding(browseDensity.heroPadding)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(heroBackground)
        .overlay(heroBorder)
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.heroPanel, style: .continuous))
        .shadowStyle(laughTrack.shadows.hero)
    }

    @ViewBuilder
    private func heroCTA(title: String) -> some View {
        let laughTrack = theme.laughTrackTokens

        if let action {
            LaughTrackButton(
                title,
                systemImage: "arrow.up.right",
                tone: .secondary,
                density: .compact,
                fullWidth: false,
                action: action
            )
        } else {
            HStack(spacing: theme.spacing.xs) {
                Image(systemName: "arrow.up.right")
                Text(title)
            }
            .font(laughTrack.typography.metadata)
            .foregroundStyle(laughTrack.colors.highlight)
        }
    }

    private var heroBackground: some View {
        let laughTrack = theme.laughTrackTokens
        return LinearGradient(
            colors: [
                laughTrack.colors.heroStart,
                laughTrack.colors.heroEnd.opacity(0.94),
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    private var heroBorder: some View {
        let laughTrack = theme.laughTrackTokens
        return RoundedRectangle(cornerRadius: laughTrack.radius.heroPanel, style: .continuous)
            .stroke(laughTrack.colors.highlight.opacity(0.2), lineWidth: 1)
    }
}

struct LaughTrackShelfHeader: View {
    let eyebrow: String?
    let title: String
    let subtitle: String?
    let actionTitle: String?
    let action: (() -> Void)?

    init(
        eyebrow: String? = nil,
        title: String,
        subtitle: String? = nil,
        actionTitle: String? = nil,
        action: (() -> Void)? = nil
    ) {
        self.eyebrow = eyebrow
        self.title = title
        self.subtitle = subtitle
        self.actionTitle = actionTitle
        self.action = action
    }

    var body: some View {
        LaughTrackSectionHeader(
            eyebrow: eyebrow,
            title: title,
            subtitle: subtitle,
            actionTitle: actionTitle,
            action: action,
            density: .compact
        )
    }
}

struct LaughTrackBrowseChip: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let systemImage: String?
    let tone: LaughTrackBrowseChipTone

    init(_ title: String, systemImage: String? = nil, tone: LaughTrackBrowseChipTone = .neutral) {
        self.title = title
        self.systemImage = systemImage
        self.tone = tone
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let browseDensity = laughTrack.browseDensity

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
        .padding(.horizontal, browseDensity.chipHorizontalPadding)
        .padding(.vertical, browseDensity.chipVerticalPadding)
        .background(backgroundColor)
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
        case .selected:
            return laughTrack.colors.textInverse
        }
    }

    private var backgroundColor: Color {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .neutral:
            return laughTrack.colors.surface
        case .accent:
            return laughTrack.colors.highlight.opacity(0.92)
        case .selected:
            return laughTrack.colors.heroStart
        }
    }

    private var borderColor: Color {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .neutral:
            return laughTrack.colors.borderSubtle
        case .accent:
            return laughTrack.colors.borderStrong.opacity(0.5)
        case .selected:
            return laughTrack.colors.heroEnd.opacity(0.42)
        }
    }
}

struct LaughTrackSearchField<TrailingAccessory: View>: View {
    @Environment(\.appTheme) private var theme

    let placeholder: String
    @Binding var text: String
    @ViewBuilder let trailingAccessory: () -> TrailingAccessory

    init(
        placeholder: String,
        text: Binding<String>,
        @ViewBuilder trailingAccessory: @escaping () -> TrailingAccessory
    ) {
        self.placeholder = placeholder
        _text = text
        self.trailingAccessory = trailingAccessory
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.sm) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: theme.iconSizes.md, weight: .semibold))
                .foregroundStyle(laughTrack.colors.textSecondary)

            TextField(placeholder, text: $text)
                .autocorrectionDisabled()
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textPrimary)

            trailingAccessory()
        }
        .padding(.horizontal, laughTrack.browseDensity.compactCardPadding)
        .padding(.vertical, theme.spacing.md)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }
}

extension LaughTrackSearchField where TrailingAccessory == EmptyView {
    init(placeholder: String, text: Binding<String>) {
        self.init(placeholder: placeholder, text: text) {
            EmptyView()
        }
    }
}

struct LaughTrackContextRow: View {
    @Environment(\.appTheme) private var theme

    let leading: String
    let trailing: String?

    init(leading: String, trailing: String? = nil) {
        self.leading = leading
        self.trailing = trailing
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.sm) {
            Text(leading)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .lineLimit(1)

            Spacer(minLength: theme.spacing.sm)

            if let trailing {
                Text(trailing)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .padding(.horizontal, laughTrack.browseDensity.chipHorizontalPadding)
                    .padding(.vertical, laughTrack.browseDensity.chipVerticalPadding)
                    .background(laughTrack.colors.highlight.opacity(0.95))
                    .overlay(
                        Capsule(style: .continuous)
                            .stroke(laughTrack.colors.borderStrong.opacity(0.45), lineWidth: 1)
                    )
                    .clipShape(Capsule(style: .continuous))
                    .lineLimit(1)
            }
        }
    }
}

struct LaughTrackResultRow: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let subtitle: String?
    let metadata: [String]
    let systemImage: String
    let imageURL: String?
    let accessoryTitle: String?
    let showsDisclosureIndicator: Bool

    init(
        title: String,
        subtitle: String? = nil,
        metadata: [String] = [],
        systemImage: String,
        imageURL: String? = nil,
        accessoryTitle: String? = nil,
        showsDisclosureIndicator: Bool = true
    ) {
        self.title = title
        self.subtitle = subtitle
        self.metadata = metadata
        self.systemImage = systemImage
        self.imageURL = imageURL
        self.accessoryTitle = accessoryTitle
        self.showsDisclosureIndicator = showsDisclosureIndicator
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let browseDensity = laughTrack.browseDensity

        HStack(spacing: browseDensity.rowGap) {
            artwork

            VStack(alignment: .leading, spacing: theme.spacing.xxs) {
                Text(title)
                    .font(laughTrack.typography.cardTitle)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(1)

                if let subtitle {
                    Text(subtitle)
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                        .lineLimit(1)
                }

                if !metadata.isEmpty {
                    Text(metadata.joined(separator: " • "))
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                        .lineLimit(1)
                }
            }

            Spacer(minLength: theme.spacing.sm)

            if let accessoryTitle {
                Text(accessoryTitle)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.accent)
                    .lineLimit(1)
            } else if showsDisclosureIndicator {
                Image(systemName: "chevron.right")
                    .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.textSecondary)
            }
        }
        .frame(maxWidth: .infinity, minHeight: browseDensity.resultRowMinHeight, alignment: .leading)
        .padding(browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens

        if let imageURL, let url = normalizedExternalURL(imageURL) {
            AsyncImage(url: url) { phase in
                switch phase {
                case .empty:
                    progressArtwork
                case .success(let image):
                    image
                        .resizable()
                        .scaledToFill()
                case .failure:
                    fallbackArtwork
                @unknown default:
                    fallbackArtwork
                }
            }
            .frame(width: 54, height: 54)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        } else {
            ZStack {
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(laughTrack.colors.surfaceMuted)

                Image(systemName: systemImage)
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
            .frame(width: 54, height: 54)
        }
    }

    private var progressArtwork: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(laughTrack.colors.surfaceMuted)
            ProgressView()
                .progressViewStyle(.circular)
                .tint(laughTrack.colors.accent)
        }
    }

    private var fallbackArtwork: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(laughTrack.colors.surfaceMuted)

            Image(systemName: systemImage)
                .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                .foregroundStyle(laughTrack.colors.accentStrong)
        }
    }

    private func normalizedExternalURL(_ rawValue: String?) -> URL? {
        guard let rawValue, !rawValue.isEmpty else { return nil }

        if let direct = URL(string: rawValue), direct.scheme != nil {
            return direct
        }

        return URL(string: "https://\(rawValue)")
    }
}

struct LaughTrackInlineStateCard: View {
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

        LaughTrackCard(tone: .muted, density: .compact) {
            VStack(alignment: .leading, spacing: theme.spacing.sm) {
                HStack(alignment: .top, spacing: theme.spacing.sm) {
                    indicator

                    VStack(alignment: .leading, spacing: theme.spacing.xxs) {
                        Text(title)
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)

                        Text(message)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                if let actionTitle, let action, tone != .loading {
                    LaughTrackButton(
                        actionTitle,
                        systemImage: tone == .error ? "arrow.clockwise" : "arrow.right",
                        tone: .secondary,
                        density: .compact,
                        fullWidth: false,
                        action: action
                    )
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
                .frame(width: 20, height: 20)
        case .empty:
            Image(systemName: "sparkles")
                .font(.system(size: theme.iconSizes.md, weight: .semibold))
                .foregroundStyle(laughTrack.colors.accentStrong)
                .frame(width: 20, height: 20)
        case .error:
            Image(systemName: "wifi.exclamationmark")
                .font(.system(size: theme.iconSizes.md, weight: .semibold))
                .foregroundStyle(laughTrack.colors.danger)
                .frame(width: 20, height: 20)
        }
    }
}

#if DEBUG
struct LaughTrackBrowseComponents_Previews: PreviewProvider {
    static var previews: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                LaughTrackHeroModule(
                    eyebrow: "Nearby",
                    title: "Comedy worth noticing near you",
                    subtitle: "Use compact browse modules to push people into Search instead of giant instructional cards.",
                    ctaTitle: "Open Search"
                )

                LaughTrackShelfHeader(
                    eyebrow: "Tonight",
                    title: "Nearby picks",
                    subtitle: "Compact browse sections should scan quickly.",
                    actionTitle: "See all"
                ) {}

                LaughTrackResultRow(
                    title: "Comedy Cellar",
                    subtitle: "New York, NY",
                    metadata: ["14 shows", "Open tonight"],
                    systemImage: "building.2"
                )

                LaughTrackBrowseChip("Upcoming dates first", systemImage: "sparkles", tone: .accent)
            }
            .padding()
        }
        .background(LaughTrackTheme().laughTrack.colors.canvas)
        .environment(\.appTheme, LaughTrackTheme())
    }
}
#endif
