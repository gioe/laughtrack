import SwiftUI
import LaughTrackBridge

enum LaughTrackBrowseChipTone: Equatable {
    case neutral
    case subtle
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
        case .selected:
            return laughTrack.colors.textInverse
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
        case .selected:
            return laughTrack.colors.heroStart
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
        .background(laughTrack.colors.surfaceMuted)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous)
                .stroke(laughTrack.colors.borderStrong.opacity(0.55), lineWidth: 1)
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

enum LaughTrackEntityRowArtworkShape: Equatable {
    case circle
    case roundedRectangle(cornerRadius: CGFloat)
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

struct LaughTrackEntityRow: View {
    @Environment(\.appTheme) private var theme

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
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.md) {
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

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens
        let rawImageURL = imageURL?.trimmingCharacters(in: .whitespacesAndNewlines)

        if let url = URL.normalizedExternalURL(rawImageURL) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
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

    let currentPage: Int
    let pageCount: Int
    let onPrevious: () -> Void
    let onNext: () -> Void

    private var isFirstPage: Bool { currentPage <= 0 }
    private var isLastPage: Bool { currentPage >= pageCount - 1 }

    var body: some View {
        HStack(spacing: theme.spacing.sm) {
            LaughTrackButton(
                "Previous",
                systemImage: "chevron.left",
                tone: .secondary,
                density: .compact,
                fullWidth: false,
                action: onPrevious
            )
            .disabled(isFirstPage)
            .opacity(isFirstPage ? 0.5 : 1)
            .accessibilityLabel("Previous page")

            Spacer(minLength: 0)

            LaughTrackBrowseChip(
                "Page \(currentPage + 1) of \(pageCount)",
                tone: .subtle
            )

            Spacer(minLength: 0)

            LaughTrackButton(
                "Next",
                systemImage: "chevron.right",
                tone: .secondary,
                density: .compact,
                fullWidth: false,
                action: onNext
            )
            .disabled(isLastPage)
            .opacity(isLastPage ? 0.5 : 1)
            .accessibilityLabel("Next page")
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
        guard !filteredItems.isEmpty else { return [] }
        let start = clampedPage * pageSize
        guard start < filteredItems.count else { return [] }
        let end = min(start + pageSize, filteredItems.count)
        return Array(filteredItems[start..<end])
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
