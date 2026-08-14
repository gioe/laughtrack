import SwiftUI
import LaughTrackBridge

enum LaughTrackBrowseChipTone: Equatable {
    case neutral
    case subtle
    case accent
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

struct LaughTrackRailCard<Content: View>: View {
    let eyebrow: String?
    let title: String?
    let subtitle: String?
    let accessibilityIdentifier: String?
    @ViewBuilder let content: Content

    @Environment(\.appTheme) private var theme

    init(
        eyebrow: String? = nil,
        title: String? = nil,
        subtitle: String? = nil,
        accessibilityIdentifier: String? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.eyebrow = eyebrow
        self.title = title
        self.subtitle = subtitle
        self.accessibilityIdentifier = accessibilityIdentifier
        self.content = content()
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.md) {
            if let title {
                if let accessibilityIdentifier {
                    LaughTrackShelfHeader(
                        eyebrow: eyebrow,
                        title: title,
                        subtitle: subtitle
                    )
                    .accessibilityIdentifier(accessibilityIdentifier)
                } else {
                    LaughTrackShelfHeader(
                        eyebrow: eyebrow,
                        title: title,
                        subtitle: subtitle
                    )
                }
            }

            content
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
        .modifier(RailAccessibilityIdentifierModifier(
            identifier: title == nil ? accessibilityIdentifier : nil
        ))
    }
}

private struct RailAccessibilityIdentifierModifier: ViewModifier {
    let identifier: String?

    func body(content: Content) -> some View {
        if let identifier {
            content.accessibilityIdentifier(identifier)
        } else {
            content
        }
    }
}

struct LaughTrackBrowseChip: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let systemImage: String?
    let tone: LaughTrackBrowseChipTone
    let isLoading: Bool

    init(_ title: String, systemImage: String? = nil, tone: LaughTrackBrowseChipTone = .neutral, isLoading: Bool = false) {
        self.title = title
        self.systemImage = systemImage
        self.tone = tone
        self.isLoading = isLoading
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let browseDensity = laughTrack.browseDensity

        HStack(spacing: theme.spacing.xs) {
            if isLoading {
                ProgressView()
                    .controlSize(.small)
            } else if let systemImage {
                Image(systemName: systemImage)
                    .font(.system(size: theme.iconSizes.sm, weight: .semibold))
            }

            Text(title)
                .font(laughTrack.typography.metadata)
                .lineLimit(2)
                .minimumScaleFactor(0.86)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
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
        case .subtle:
            return laughTrack.colors.textSecondary
        case .accent:
            return laughTrack.colors.accentStrong
        }
    }

    private var backgroundColor: Color {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .neutral:
            return laughTrack.colors.surface
        case .subtle:
            return laughTrack.colors.surfaceMuted.opacity(0.68)
        case .accent:
            return laughTrack.colors.highlight.opacity(0.92)
        }
    }

    private var borderColor: Color {
        let laughTrack = theme.laughTrackTokens

        switch tone {
        case .neutral:
            return laughTrack.colors.borderSubtle
        case .subtle:
            return laughTrack.colors.borderSubtle.opacity(0.5)
        case .accent:
            return laughTrack.colors.borderStrong.opacity(0.5)
        }
    }
}

/// A horizontal row of selectable chips: the selected option renders as an
/// accent-toned `LaughTrackBrowseChip` with the `.isSelected` trait, the rest
/// as neutral. Shared by the comedian-detail tab picker and the two
/// distance pickers so tone and accessibility changes happen in one spot.
/// Selection side effects beyond assignment belong in the binding's setter
/// (see ComedianDetailView, which routes through activate(_:)).
struct LaughTrackChipPicker<Option: Hashable>: View {
    @Environment(\.appTheme) private var theme

    let options: [Option]
    @Binding var selection: Option
    let accessibilityLabel: String
    let accessibilityIdentifier: String
    let title: (Option) -> String

    init(
        options: [Option],
        selection: Binding<Option>,
        accessibilityLabel: String,
        accessibilityIdentifier: String,
        title: @escaping (Option) -> String
    ) {
        self.options = options
        self._selection = selection
        self.accessibilityLabel = accessibilityLabel
        self.accessibilityIdentifier = accessibilityIdentifier
        self.title = title
    }

    var body: some View {
        HStack(spacing: theme.spacing.sm) {
            ForEach(options, id: \.self) { option in
                Button {
                    selection = option
                } label: {
                    LaughTrackBrowseChip(title(option), tone: tone(for: option))
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(selection == option ? [.isSelected] : [])
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityIdentifier(accessibilityIdentifier)
    }

    func tone(for option: Option) -> LaughTrackBrowseChipTone {
        selection == option ? .accent : .neutral
    }
}

struct LaughTrackSearchField<TrailingAccessory: View>: View {
    @Environment(\.appTheme) private var theme

    let placeholder: String
    let accessibilityIdentifier: String?
    @Binding var text: String
    @ViewBuilder let trailingAccessory: () -> TrailingAccessory

    init(
        placeholder: String,
        text: Binding<String>,
        accessibilityIdentifier: String? = nil,
        @ViewBuilder trailingAccessory: @escaping () -> TrailingAccessory
    ) {
        self.placeholder = placeholder
        self.accessibilityIdentifier = accessibilityIdentifier
        _text = text
        self.trailingAccessory = trailingAccessory
    }

    @ViewBuilder
    var body: some View {
        if let accessibilityIdentifier {
            searchFieldChrome.accessibilityIdentifier(accessibilityIdentifier)
        } else {
            searchFieldChrome
        }
    }

    private var searchFieldChrome: some View {
        let laughTrack = theme.laughTrackTokens

        return HStack(spacing: theme.spacing.sm) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: theme.iconSizes.md, weight: .semibold))
                .foregroundStyle(laughTrack.colors.textSecondary)

            searchInput

            trailingAccessory()
        }
        .padding(.horizontal, laughTrack.browseDensity.compactCardPadding)
        .padding(.vertical, theme.spacing.md)
        .background(laughTrack.colors.surfaceMuted)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous)
                .stroke(laughTrack.colors.borderStrong.opacity(0.55), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    @ViewBuilder
    private var searchInput: some View {
        let laughTrack = theme.laughTrackTokens
        let field = TextField(placeholder, text: $text)
            .autocorrectionDisabled()
            .font(laughTrack.typography.body)
            .foregroundStyle(laughTrack.colors.textPrimary)

        if let accessibilityIdentifier {
            field.accessibilityIdentifier(accessibilityIdentifier)
        } else {
            field
        }
    }
}

extension LaughTrackSearchField where TrailingAccessory == EmptyView {
    init(placeholder: String, text: Binding<String>, accessibilityIdentifier: String? = nil) {
        self.init(
            placeholder: placeholder,
            text: text,
            accessibilityIdentifier: accessibilityIdentifier
        ) {
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

enum LaughTrackEntityRowArtworkShape: Equatable {
    case circle
    case roundedRectangle(cornerRadius: CGFloat)
}

enum LaughTrackSearchEntityKind: Equatable {
    case comedian
    case club
    case podcast

    var fallback: ArtworkFallbackKind {
        switch self {
        case .comedian: return .comedian
        case .club: return .club
        case .podcast: return .podcast
        }
    }
}

/// The canonical rich entity row shared by Search and Library.
struct LaughTrackSearchEntityRowMetrics: Equatable {
    let verticalCardPadding: CGFloat
    let titleLineLimit: Int
    let subtitleLineLimit: Int

    static let standard = Self(
        verticalCardPadding: 4,
        titleLineLimit: 2,
        subtitleLineLimit: 2
    )
}

struct LaughTrackSearchEntityRow<TrailingAccessory: View>: View {
    let title: String
    let subtitle: String?
    let imageURL: String?
    let kind: LaughTrackSearchEntityKind
    let action: () -> Void
    let accessibilityIdentifier: String?
    let trailingAccessory: TrailingAccessory
    let hasTrailingAccessory: Bool

    @Environment(\.appTheme) private var theme

    init(
        title: String,
        subtitle: String? = nil,
        imageURL: String?,
        kind: LaughTrackSearchEntityKind,
        action: @escaping () -> Void,
        accessibilityIdentifier: String? = nil
    ) where TrailingAccessory == EmptyView {
        self.title = title
        self.subtitle = subtitle
        self.imageURL = imageURL
        self.kind = kind
        self.action = action
        self.accessibilityIdentifier = accessibilityIdentifier
        self.trailingAccessory = EmptyView()
        self.hasTrailingAccessory = false
    }

    init(
        title: String,
        subtitle: String? = nil,
        imageURL: String?,
        kind: LaughTrackSearchEntityKind,
        action: @escaping () -> Void,
        accessibilityIdentifier: String? = nil,
        @ViewBuilder trailingAccessory: () -> TrailingAccessory
    ) {
        self.title = title
        self.subtitle = subtitle
        self.imageURL = imageURL
        self.kind = kind
        self.action = action
        self.accessibilityIdentifier = accessibilityIdentifier
        self.trailingAccessory = trailingAccessory()
        self.hasTrailingAccessory = true
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let metrics = LaughTrackSearchEntityRowMetrics.standard

        HStack(spacing: theme.spacing.md) {
            Button(action: action) {
                HStack(spacing: theme.spacing.md) {
                    artwork

                    VStack(alignment: .leading, spacing: 4) {
                        Text(title)
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .lineLimit(metrics.titleLineLimit)
                            .fixedSize(horizontal: false, vertical: true)

                        if let subtitle, !subtitle.isEmpty {
                            Text(subtitle)
                                .font(laughTrack.typography.metadata)
                                .foregroundStyle(laughTrack.colors.textSecondary)
                                .lineLimit(metrics.subtitleLineLimit)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    Image(systemName: "chevron.right")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.textSecondary)
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity, alignment: .leading)
            .accessibilityLabel(rowAccessibilityLabel)
            .accessibilityIdentifier(accessibilityIdentifier ?? "")

            if hasTrailingAccessory {
                trailingAccessory
            }
        }
        .padding(.horizontal, laughTrack.browseDensity.compactCardPadding)
        .padding(.vertical, metrics.verticalCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderStrong.opacity(0.9), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    private var rowAccessibilityLabel: String {
        guard let subtitle = subtitle?.trimmingCharacters(in: .whitespacesAndNewlines),
              !subtitle.isEmpty
        else { return title }
        return "\(title), \(subtitle)"
    }

    @ViewBuilder
    private var artwork: some View {
        switch kind {
        case .comedian:
            ClubWallHeadshotFrame(
                caption: title,
                captionVisibility: .hidden,
                photoWidth: 64,
                photoHeight: 61,
                frameWidth: 76,
                frameHeight: 73
            ) {
                artworkImage
            }
        case .club, .podcast:
            framedPoster
        }
    }

    private var framedPoster: some View {
        let frameColor = kind == .club
            ? Color(red: 1.0, green: 0.78, blue: 0.24)
            : theme.laughTrackTokens.colors.accentStrong

        return ZStack {
            artworkImage
                .frame(width: 64, height: 64)
                .clipShape(RoundedRectangle(cornerRadius: kind == .club ? 8 : 5, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: kind == .club ? 8 : 5, style: .continuous)
                        .stroke(Color.black.opacity(0.55), lineWidth: 1)
                )

            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .strokeBorder(
                    frameColor,
                    style: StrokeStyle(
                        lineWidth: 1.5,
                        lineCap: .round,
                        lineJoin: .round,
                        dash: kind == .club ? [1.2, 10] : [0.5, 4.5]
                    )
                )
                .frame(width: 69, height: 69)
                .shadow(color: frameColor.opacity(0.5), radius: 3)
                .shadow(color: frameColor.opacity(0.25), radius: 7)
        }
        .frame(width: 69, height: 69)
    }

    @ViewBuilder
    private var artworkImage: some View {
        let laughTrack = theme.laughTrackTokens
        let trimmed = imageURL?.trimmingCharacters(in: .whitespacesAndNewlines)

        if let url = URL.normalizedExternalURL(trimmed) {
            CachedAsyncImage(url: url) { image in
                if kind == .club {
                    image.resizable().scaledToFit()
                } else {
                    image.resizable().scaledToFill()
                }
            } placeholder: {
                Rectangle()
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay { ProgressView().tint(laughTrack.colors.accent) }
            } error: { _ in
                fallbackArtwork
            }
        } else {
            fallbackArtwork
        }
    }

    private var fallbackArtwork: some View {
        Rectangle()
            .fill(theme.laughTrackTokens.colors.surfaceMuted)
            .overlay {
                Image(systemName: kind.fallback.systemImage)
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(theme.laughTrackTokens.colors.accentStrong)
            }
    }
}

struct LaughTrackEntityRowDesign: Equatable {
    var artworkSize: CGFloat
    var artworkShape: LaughTrackEntityRowArtworkShape
    var minHeight: CGFloat
    var titleLineLimit: Int
    var subtitleLineLimit: Int
    var metadataLineLimit: Int

    static let searchCard = Self(
        artworkSize: 70,
        artworkShape: .circle,
        minHeight: 86,
        titleLineLimit: 2,
        subtitleLineLimit: 2,
        metadataLineLimit: 2
    )

    static let savedEntity = Self(
        artworkSize: 70,
        artworkShape: .roundedRectangle(cornerRadius: 12),
        minHeight: 86,
        titleLineLimit: 2,
        subtitleLineLimit: 1,
        metadataLineLimit: 1
    )
}

struct LaughTrackEntityRow<TrailingAccessory: View>: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let subtitle: String?
    let metadata: [String]
    let systemImage: String
    let imageURL: String?
    let accessoryTitle: String?
    let showsDisclosureIndicator: Bool
    let design: LaughTrackEntityRowDesign
    let action: (() -> Void)?
    let trailingAccessory: TrailingAccessory
    let hasTrailingAccessory: Bool

    init(
        title: String,
        subtitle: String? = nil,
        metadata: [String] = [],
        systemImage: String,
        imageURL: String? = nil,
        accessoryTitle: String? = nil,
        showsDisclosureIndicator: Bool = false,
        design: LaughTrackEntityRowDesign = .searchCard
    ) where TrailingAccessory == EmptyView {
        self.title = title
        self.subtitle = subtitle
        self.metadata = metadata
        self.systemImage = systemImage
        self.imageURL = imageURL
        self.accessoryTitle = accessoryTitle
        self.showsDisclosureIndicator = showsDisclosureIndicator
        self.design = design
        self.action = nil
        self.trailingAccessory = EmptyView()
        self.hasTrailingAccessory = false
    }

    init(
        title: String,
        subtitle: String? = nil,
        metadata: [String] = [],
        systemImage: String,
        imageURL: String? = nil,
        accessoryTitle: String? = nil,
        showsDisclosureIndicator: Bool = false,
        design: LaughTrackEntityRowDesign = .searchCard,
        action: (() -> Void)? = nil,
        @ViewBuilder trailingAccessory: () -> TrailingAccessory
    ) {
        self.title = title
        self.subtitle = subtitle
        self.metadata = metadata
        self.systemImage = systemImage
        self.imageURL = imageURL
        self.accessoryTitle = accessoryTitle
        self.showsDisclosureIndicator = showsDisclosureIndicator
        self.design = design
        self.action = action
        self.trailingAccessory = trailingAccessory()
        self.hasTrailingAccessory = true
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.md) {
            if let action {
                Button(action: action) {
                    rowContent
                }
                .buttonStyle(.plain)
                .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                rowContent
            }

            if hasTrailingAccessory {
                trailingAccessory
            }
        }
        .frame(maxWidth: .infinity, minHeight: design.minHeight, alignment: .leading)
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceMuted)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderStrong.opacity(0.55), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    private var rowContent: some View {
        let laughTrack = theme.laughTrackTokens

        return HStack(spacing: theme.spacing.md) {
            artwork

            VStack(alignment: .leading, spacing: theme.spacing.xxs) {
                Text(title)
                    .font(laughTrack.typography.cardTitle)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(design.titleLineLimit)
                    .fixedSize(horizontal: false, vertical: true)

                if let subtitle {
                    Text(subtitle)
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                        .lineLimit(design.subtitleLineLimit)
                        .fixedSize(horizontal: false, vertical: true)
                }

                if !metadata.isEmpty {
                    Text(metadata.joined(separator: " • "))
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                        .lineLimit(design.metadataLineLimit)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .layoutPriority(1)

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
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens
        let rawImageURL = imageURL?.trimmingCharacters(in: .whitespacesAndNewlines)

        if let url = URL.normalizedExternalURL(rawImageURL) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFit()
            } placeholder: {
                artworkBackground
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                fallbackArtwork
            }
            .frame(width: design.artworkSize, height: design.artworkSize)
            .background(artworkBackground)
            .modifier(LaughTrackEntityArtworkClip(shape: design.artworkShape))
        } else {
            fallbackArtwork
        }
    }

    @ViewBuilder
    private var artworkBackground: some View {
        let laughTrack = theme.laughTrackTokens

        switch design.artworkShape {
        case .circle:
            Circle()
                .fill(laughTrack.colors.surfaceMuted)
        case .roundedRectangle(let cornerRadius):
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .fill(laughTrack.colors.surfaceMuted)
        }
    }

    private var fallbackArtwork: some View {
        artworkBackground
            .overlay {
                Image(systemName: systemImage)
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(theme.laughTrackTokens.colors.accentStrong)
            }
            .frame(width: design.artworkSize, height: design.artworkSize)
    }
}

private struct LaughTrackEntityArtworkClip: ViewModifier {
    let shape: LaughTrackEntityRowArtworkShape

    @ViewBuilder
    func body(content: Content) -> some View {
        switch shape {
        case .circle:
            content.clipShape(Circle())
        case .roundedRectangle(let cornerRadius):
            content.clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
        }
    }
}

struct LaughTrackResultRow: View {
    let title: String
    let subtitle: String?
    let metadata: [String]
    let systemImage: String
    let imageURL: String?
    let accessoryTitle: String?
    let showsDisclosureIndicator: Bool
    let design: LaughTrackEntityRowDesign

    init(
        title: String,
        subtitle: String? = nil,
        metadata: [String] = [],
        systemImage: String,
        imageURL: String? = nil,
        accessoryTitle: String? = nil,
        showsDisclosureIndicator: Bool = false,
        design: LaughTrackEntityRowDesign = .searchCard
    ) {
        self.title = title
        self.subtitle = subtitle
        self.metadata = metadata
        self.systemImage = systemImage
        self.imageURL = imageURL
        self.accessoryTitle = accessoryTitle
        self.showsDisclosureIndicator = showsDisclosureIndicator
        self.design = design
    }

    var body: some View {
        LaughTrackEntityRow(
            title: title,
            subtitle: subtitle,
            metadata: metadata,
            systemImage: systemImage,
            imageURL: imageURL,
            accessoryTitle: accessoryTitle,
            showsDisclosureIndicator: showsDisclosureIndicator,
            design: design
        )
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

                        if !message.isEmpty {
                            Text(message)
                                .font(laughTrack.typography.metadata)
                                .foregroundStyle(laughTrack.colors.textSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
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

struct LaughTrackPagedControls: View {
    @Environment(\.appTheme) private var theme
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    let currentPage: Int
    let pageCount: Int
    let onPrevious: () -> Void
    let onNext: () -> Void
    let accessibilityIdentifierPrefix: String?

    init(
        currentPage: Int,
        pageCount: Int,
        onPrevious: @escaping () -> Void,
        onNext: @escaping () -> Void,
        accessibilityIdentifierPrefix: String? = nil
    ) {
        self.currentPage = currentPage
        self.pageCount = pageCount
        self.onPrevious = onPrevious
        self.onNext = onNext
        self.accessibilityIdentifierPrefix = accessibilityIdentifierPrefix
    }

    private var isFirstPage: Bool { currentPage <= 0 }
    private var isLastPage: Bool { currentPage >= pageCount - 1 }
    private var pageLabel: String { "Page \(currentPage + 1) of \(pageCount)" }

    @ViewBuilder
    var body: some View {
        if LaughTrackPagedControlsPresentation.resolve(for: dynamicTypeSize) == .compact {
            compactControls
        } else {
            ViewThatFits(in: .horizontal) {
                expandedControls
                compactControls
            }
        }
    }

    private var expandedControls: some View {
        HStack(spacing: theme.spacing.sm) {
            expandedButton(
                "Previous",
                systemImage: "chevron.left",
                isDisabled: isFirstPage,
                identifierSuffix: "previous",
                action: onPrevious
            )

            Spacer(minLength: 0)

            pageStatus

            Spacer(minLength: 0)

            expandedButton(
                "Next",
                systemImage: "chevron.right",
                isDisabled: isLastPage,
                identifierSuffix: "next",
                action: onNext
            )
        }
    }

    private var compactControls: some View {
        VStack(spacing: theme.spacing.sm) {
            pageStatus

            HStack(spacing: theme.spacing.sm) {
                compactButton(
                    systemImage: "chevron.left",
                    accessibilityLabel: "Previous page",
                    isDisabled: isFirstPage,
                    identifierSuffix: "previous",
                    action: onPrevious
                )

                Spacer(minLength: 0)

                compactButton(
                    systemImage: "chevron.right",
                    accessibilityLabel: "Next page",
                    isDisabled: isLastPage,
                    identifierSuffix: "next",
                    action: onNext
                )
            }
        }
    }

    private var pageStatus: some View {
        LaughTrackBrowseChip(pageLabel, tone: .subtle)
            .accessibilityLabel(pageLabel)
            .modifier(PagedControlAccessibilityIdentifierModifier(
                identifier: accessibilityIdentifierPrefix.map { "\($0).current" }
            ))
    }

    private func expandedButton(
        _ title: String,
        systemImage: String,
        isDisabled: Bool,
        identifierSuffix: String,
        action: @escaping () -> Void
    ) -> some View {
        LaughTrackButton(
            title,
            systemImage: systemImage,
            tone: .secondary,
            density: .compact,
            fullWidth: false,
            action: action
        )
            .fixedSize(horizontal: true, vertical: false)
            .disabled(isDisabled)
            .opacity(isDisabled ? 0.5 : 1)
            .accessibilityLabel("\(title) page")
            .modifier(PagedControlAccessibilityIdentifierModifier(
                identifier: accessibilityIdentifierPrefix.map { "\($0).\(identifierSuffix)" }
            ))
    }

    private func compactButton(
        systemImage: String,
        accessibilityLabel: String,
        isDisabled: Bool,
        identifierSuffix: String,
        action: @escaping () -> Void
    ) -> some View {
        let laughTrack = theme.laughTrackTokens

        return Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                .foregroundStyle(laughTrack.colors.textPrimary)
                .frame(width: 44, height: 44)
                .background(laughTrack.colors.surfaceElevated)
                .overlay(
                    Capsule(style: .continuous)
                        .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                )
                .clipShape(Capsule(style: .continuous))
        }
        .buttonStyle(.plain)
        .disabled(isDisabled)
        .opacity(isDisabled ? 0.5 : 1)
        .accessibilityLabel(accessibilityLabel)
        .modifier(PagedControlAccessibilityIdentifierModifier(
            identifier: accessibilityIdentifierPrefix.map { "\($0).\(identifierSuffix)" }
        ))
    }
}

enum LaughTrackPagedControlsPresentation: Equatable {
    case expanded
    case compact

    static func resolve(for dynamicTypeSize: DynamicTypeSize) -> Self {
        dynamicTypeSize.isAccessibilitySize ? .compact : .expanded
    }
}

private struct PagedControlAccessibilityIdentifierModifier: ViewModifier {
    let identifier: String?

    func body(content: Content) -> some View {
        if let identifier {
            content.accessibilityIdentifier(identifier)
        } else {
            content
        }
    }
}

struct FavoriteSearchableSection<Item, ID: Hashable, Row: View>: View {
    static var defaultPageSize: Int { 20 }

    @Environment(\.appTheme) private var theme

    let items: [Item]
    let idKeyPath: KeyPath<Item, ID>
    let searchPlaceholder: String
    let pageSize: Int
    let matchesQuery: (Item, String) -> Bool
    let row: (Item) -> Row

    @State private var query = ""
    @State private var page = 0

    init(
        items: [Item],
        id idKeyPath: KeyPath<Item, ID>,
        searchPlaceholder: String,
        pageSize: Int = Self.defaultPageSize,
        matchesQuery: @escaping (Item, String) -> Bool,
        @ViewBuilder row: @escaping (Item) -> Row
    ) {
        self.items = items
        self.idKeyPath = idKeyPath
        self.searchPlaceholder = searchPlaceholder
        self.pageSize = pageSize
        self.matchesQuery = matchesQuery
        self.row = row
    }

    private var trimmedQuery: String {
        query.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var filteredItems: [Item] {
        guard !trimmedQuery.isEmpty else { return items }
        return items.filter { matchesQuery($0, trimmedQuery) }
    }

    private var pageCount: Int {
        guard !filteredItems.isEmpty else { return 1 }
        return Int(ceil(Double(filteredItems.count) / Double(pageSize)))
    }

    private var clampedPage: Int {
        max(0, min(page, pageCount - 1))
    }

    private var pagedItems: [Item] {
        Self.pagedItems(
            items: filteredItems,
            page: clampedPage,
            pageSize: pageSize
        )
    }

    static func pagedItems(
        items: [Item],
        query: String,
        page: Int,
        pageSize: Int,
        matchesQuery: (Item, String) -> Bool
    ) -> [Item] {
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        let filteredItems = trimmedQuery.isEmpty ? items : items.filter { matchesQuery($0, trimmedQuery) }
        let pageCount = filteredItems.isEmpty ? 1 : Int(ceil(Double(filteredItems.count) / Double(pageSize)))
        let clampedPage = max(0, min(page, pageCount - 1))
        return Self.pagedItems(
            items: filteredItems,
            page: clampedPage,
            pageSize: pageSize
        )
    }

    private static func pagedItems(
        items: [Item],
        page: Int,
        pageSize: Int
    ) -> [Item] {
        guard !items.isEmpty else { return [] }
        let start = page * pageSize
        guard start < items.count else { return [] }
        let end = min(start + pageSize, items.count)
        return Array(items[start..<end])
    }

    var body: some View {
        let tokens = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: tokens.spacing.itemGap) {
            LaughTrackSearchField(placeholder: searchPlaceholder, text: $query)

            if filteredItems.isEmpty {
                LaughTrackStateView(
                    tone: .empty,
                    title: "No matches",
                    message: "Try a different search."
                )
            } else {
                ForEach(pagedItems, id: idKeyPath) { item in
                    row(item)
                }

                if pageCount > 1 {
                    LaughTrackPagedControls(
                        currentPage: clampedPage,
                        pageCount: pageCount,
                        onPrevious: {
                            let next = clampedPage - 1
                            if next >= 0 { page = next }
                        },
                        onNext: {
                            let next = clampedPage + 1
                            if next < pageCount { page = next }
                        }
                    )
                }
            }
        }
        .onChange(of: query) { _ in
            page = 0
        }
        .onChange(of: items.count) { _ in
            page = min(page, max(0, pageCount - 1))
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
                LaughTrackBrowseChip("Tonight", systemImage: "moon.stars", tone: .subtle)
            }
            .padding()
        }
        .background(LaughTrackTheme().laughTrack.colors.canvas)
        .environment(\.appTheme, LaughTrackTheme())
    }
}
#endif
