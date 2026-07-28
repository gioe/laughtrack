import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct HomeShowsTonightRail: View {
    let railKind: HomeShowRailKind
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let searchNavigationBridge: SearchNavigationBridge
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache
    let onInitialHomeLoadComplete: (() -> Void)?

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @StateObject private var model = HomeShowsTonightModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    private var distanceMiles: Int? {
        nearbyPreferenceStore.preference?.distanceMiles
    }

    var body: some View {
        HomeDiscoverRailCard(
            variant: railKind == .showsTonight ? .spotlight : .scheduleBoard,
            eyebrow: railKind.eyebrow,
            title: title,
            subtitle: railKind.subtitle,
            accessibilityIdentifier: railKind.railAccessibilityIdentifier
        ) {
            switch model.phase {
            case .idle, .loading:
                ShowsListSkeleton(rowCount: 3)
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: {
                        await model.refresh(
                            railKind: railKind,
                            apiClient: apiClient,
                            zipCode: zipCode,
                            distanceMiles: distanceMiles,
                            cache: cache,
                            persistentCache: persistentCache
                        )
                    },
                    signIn: { coordinator.push(.profile) }
                )
            case .success(let shows):
                if shows.isEmpty {
                    EmptyCard(message: railKind.emptyMessage)
                } else {
                    showsContent(shows)
                }
            }
        }
        .task(id: model.requestKey(for: zipCode, distanceMiles: distanceMiles, railKind: railKind)) {
            await model.refresh(
                railKind: railKind,
                apiClient: apiClient,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                cache: cache,
                persistentCache: persistentCache
            )
            if railKind == .showsTonight {
                nearbyPreferenceStore.setDefaultPreference(model.feedNearbyPreference)
            }
        }
        .task(id: hasFinishedInitialLoad) {
            guard railKind == .showsTonight, hasFinishedInitialLoad else { return }
            onInitialHomeLoadComplete?()
        }
    }

    private var title: String? {
        railKind.title
    }

    private var hasFinishedInitialLoad: Bool {
        switch model.phase {
        case .idle, .loading:
            return false
        case .success, .failure:
            return true
        }
    }

    @ViewBuilder
    private func showsContent(_ shows: [Components.Schemas.Show]) -> some View {
        if railKind == .showsTonight {
            HomeShowsTonightCarousel(shows: shows)
        } else {
            VStack(spacing: theme.spacing.sm) {
                ForEach(shows, id: \.id) { show in
                    Button {
                        coordinator.open(.show(show.id))
                    } label: {
                        ShowRow(show: show, presentation: .compactTicket)
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier(LaughTrackViewTestID.homeShowsTonightButton(show.id))
                }
            }
        }

        LaughTrackButton("See more", systemImage: "magnifyingglass", tone: .secondary, density: .compact) {
            searchNavigationBridge.openSearch(
                HomeShowsTonightModel.seeMoreSearchSeed(
                    railKind: railKind,
                    nearbyPreference: seeMoreNearbyPreference
                )
            )
        }
        .accessibilityIdentifier(railKind.seeMoreAccessibilityIdentifier)
    }

    private var seeMoreNearbyPreference: NearbyPreference? {
        nearbyPreferenceStore.preference ?? model.feedNearbyPreference
    }
}

private struct HomeShowsTonightCarousel: View {
    let shows: [Components.Schemas.Show]

    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme
    @State private var selectedShowID: Int?

    var body: some View {
        #if os(iOS)
        VStack(spacing: theme.spacing.xs) {
            GeometryReader { proxy in
                let pageWidth = min(proxy.size.width, max(0, UIScreen.main.bounds.width - 64))
                let laughTrack = theme.laughTrackTokens
                let contentWidth = max(
                    0,
                    pageWidth - (laughTrack.browseDensity.compactCardPadding * 2)
                )

                VStack(alignment: .center, spacing: theme.spacing.md) {
                    Text("TONIGHT!")
                        .font(.system(size: 22, weight: .heavy, design: .rounded))
                        .tracking(2.4)
                        .textCase(.uppercase)
                        .foregroundStyle(laughTrack.colors.accentStrong)
                        .shadow(color: laughTrack.colors.accentStrong.opacity(0.4), radius: 6)

                    ZStack(alignment: .top) {
                        HomeMarqueeStageBackground(glowRadius: 200, glowOpacity: 0.22)
                            .frame(height: HomeShowsTonightCarouselLayout.stageHeight)
                            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))

                        HStack(spacing: 0) {
                            carouselButtons(pageWidth: contentWidth)
                        }
                        .offset(x: -CGFloat(selectedShowIndex) * contentWidth)
                        .animation(.snappy(duration: 0.25), value: selectedShowIndex)
                        .frame(width: contentWidth, alignment: .leading)
                        .clipped()
                        .highPriorityGesture(pagerDragGesture(pageWidth: contentWidth))
                    }
                    .frame(width: contentWidth)
                    .clipped()

                    HomeShowsTonightPageIndicator(
                        count: shows.count,
                        selectedIndex: selectedShowIndex
                    )
                }
                .padding(laughTrack.browseDensity.compactCardPadding)
                .frame(width: pageWidth, height: 456, alignment: .top)
                .background(laughTrack.colors.surface)
                .overlay(
                    RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                        .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
            }
            .frame(height: 456)
        }
        #else
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: theme.spacing.sm) {
                carouselButtons(pageWidth: 320)
                    .frame(width: 320)
            }
        }
        #endif
    }

    private func carouselButtons(pageWidth: CGFloat) -> some View {
        ForEach(shows, id: \.id) { show in
            Button {
                coordinator.open(.show(show.id))
            } label: {
                HomeShowsTonightHeroCard(
                    show: show,
                    width: pageWidth
                )
                    .frame(width: pageWidth)
            }
            .frame(width: pageWidth)
            .clipped()
            .buttonStyle(.plain)
            .accessibilityIdentifier(show.id == shows.first?.id ? LaughTrackViewTestID.homeShowsTonightHeroButton : LaughTrackViewTestID.homeShowsTonightButton(show.id))
            .tag(show.id)
        }
    }

    private var selectedShowIndex: Int {
        guard let selectedID = selectedShowID ?? shows.first?.id,
              let index = shows.firstIndex(where: { $0.id == selectedID })
        else {
            return 0
        }

        return index
    }

    private func pagerDragGesture(pageWidth: CGFloat) -> some Gesture {
        DragGesture(minimumDistance: 20)
            .onEnded { value in
                let nextIndex = HomeHorizontalPagerDrag.nextIndex(
                    currentIndex: selectedShowIndex,
                    itemCount: shows.count,
                    pageWidth: pageWidth,
                    translation: value.translation
                )
                selectedShowID = shows[nextIndex].id
            }
    }
}

private enum HomeShowsTonightCarouselLayout {
    static let stageHeight: CGFloat = 198
}

enum HomeHorizontalPagerDrag {
    static func nextIndex(
        currentIndex: Int,
        itemCount: Int,
        pageWidth: CGFloat,
        translation: CGSize
    ) -> Int {
        guard itemCount > 0 else { return 0 }
        let safeCurrentIndex = max(0, min(currentIndex, itemCount - 1))
        guard abs(translation.width) > abs(translation.height) else {
            return safeCurrentIndex
        }

        let threshold = pageWidth * 0.2
        if translation.width < -threshold {
            return min(itemCount - 1, safeCurrentIndex + 1)
        }
        if translation.width > threshold {
            return max(0, safeCurrentIndex - 1)
        }
        return safeCurrentIndex
    }
}

private struct HomeShowsTonightPageIndicator: View {
    let count: Int
    let selectedIndex: Int

    @Environment(\.appTheme) private var theme

    var body: some View {
        HStack(spacing: 6) {
            ForEach(0..<count, id: \.self) { index in
                Circle()
                    .fill(
                        index == selectedIndex
                            ? theme.laughTrackTokens.colors.textPrimary
                            : theme.laughTrackTokens.colors.textSecondary.opacity(0.45)
                    )
                    .frame(width: 7, height: 7)
            }
        }
        .frame(height: count > 1 ? 12 : 0)
        .opacity(count > 1 ? 1 : 0)
        .accessibilityHidden(true)
    }
}

private struct HomeShowsTonightHeroCard: View {
    let show: Components.Schemas.Show
    var width: CGFloat?

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .center, spacing: theme.spacing.md) {
            artwork

            VStack(alignment: .center, spacing: 10) {
                Text(timeLabel)
                    .font(.system(size: 30, weight: .heavy, design: .rounded))
                    .tracking(0.5)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(1)
                    .shadow(color: .black.opacity(0.35), radius: 2, y: 1)

                Text(ShowTitlePresentation.title(for: show))
                    .font(.system(size: 16, weight: .heavy, design: .rounded))
                    .tracking(0.4)
                    .textCase(.uppercase)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)

                Text(venueLine)
                    .font(.system(size: 9, weight: .semibold, design: .rounded))
                    .tracking(2)
                    .textCase(.uppercase)
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
                    .minimumScaleFactor(0.8)
                    .fixedSize(horizontal: false, vertical: true)

                if let priceLabel {
                    Text(priceLabel)
                        .font(laughTrack.typography.body.weight(.heavy))
                        .foregroundStyle(Color.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 5)
                        .background(laughTrack.colors.accentStrong)
                        .clipShape(Capsule(style: .continuous))
                        .shadow(color: laughTrack.colors.accentStrong.opacity(0.45), radius: 6, y: 2)
                        .padding(.top, 4)
                }
            }
            .frame(maxWidth: .infinity)
        }
        .frame(width: width, alignment: .leading)
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(ShowTitlePresentation.title(for: show)), \(show.clubName ?? "Unknown club"), \(accessibilityMetadata.joined(separator: ", "))")
    }

    @ViewBuilder
    private var artwork: some View {
        GeometryReader { proxy in
            let metrics = portraitMetrics(for: proxy.size.width)

            ClubWallHeadshotFrame(
                caption: headshotCaption,
                photoWidth: metrics.photoWidth,
                photoHeight: metrics.photoHeight,
                frameWidth: metrics.frameWidth,
                frameHeight: metrics.frameHeight,
                captionFontSize: metrics.captionFontSize,
                captionWidth: metrics.captionWidth,
                captionHeight: metrics.captionHeight
            ) {
                artworkImage
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(maxWidth: .infinity)
        .frame(height: HomeShowsTonightCarouselLayout.stageHeight)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    @ViewBuilder
    private var artworkImage: some View {
        let laughTrack = theme.laughTrackTokens

        if let url = HomeShowsTonightHeroPresentation.artworkImageURL(for: show).flatMap(URL.normalizedExternalURL) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                Rectangle()
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                fallbackArtwork
            }
        } else {
            fallbackArtwork
        }
    }

    private var fallbackArtwork: some View {
        let laughTrack = theme.laughTrackTokens

        return Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: ArtworkFallbackKind.show.systemImage)
                    .font(.system(size: 28, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

    private var timeLabel: String {
        ShowFormatting.dateStack(show.date, timezoneID: show.timezone).time
    }

    private var headshotCaption: String {
        HomeShowsTonightHeroPresentation.headshotCaption(for: show)
    }

    private func portraitMetrics(for availableWidth: CGFloat) -> HomeShowsTonightPortraitMetrics {
        let scale = min(1.0, max(0.84, availableWidth / 300))

        return HomeShowsTonightPortraitMetrics(
            photoWidth: 138 * scale,
            photoHeight: 132 * scale,
            frameWidth: 154 * scale,
            frameHeight: 170 * scale,
            captionFontSize: 8.5 * scale,
            captionWidth: 126 * scale,
            captionHeight: 17 * scale
        )
    }

    private var roomLabel: String? {
        // Delegates so the club-name-duplicate suppression in
        // ShowRow.roomLabel applies to the hero venue line too.
        ShowRow.roomLabel(for: show)
    }

    private var venueLine: String {
        let venue = show.clubName ?? "Unknown club"
        guard let roomLabel else { return "At \(venue)" }
        return "At \(venue) • \(roomLabel)"
    }

    private var priceLabel: String? {
        let trimmed = ShowRow.priceLabel(for: show)?.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let trimmed, !trimmed.isEmpty else { return nil }
        return trimmed
    }

    private var accessibilityMetadata: [String] {
        [timeLabel, roomLabel, priceLabel].compactMap { $0 }
    }

}

struct HomeShowsTonightPortraitMetrics {
    let photoWidth: CGFloat
    let photoHeight: CGFloat
    let frameWidth: CGFloat
    let frameHeight: CGFloat
    let captionFontSize: CGFloat
    let captionWidth: CGFloat
    let captionHeight: CGFloat
}

enum HomeShowsTonightHeroPresentation {
    static func shouldShowFooter(for show: Components.Schemas.Show) -> Bool {
        false
    }

    static func artworkImageURL(for show: Components.Schemas.Show) -> String? {
        if let comedianImageURL = artworkComedian(for: show)?.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty {
            return comedianImageURL
        }

        return show.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
    }

    static func headshotCaption(for show: Components.Schemas.Show) -> String {
        if let comedianName = artworkComedian(for: show)?.name.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty {
            return comedianName
        }

        return ShowTitlePresentation.title(for: show)
    }

    private static func artworkComedian(for show: Components.Schemas.Show) -> Components.Schemas.ComedianLineup? {
        if let showImageComedian = lineupComedianMatchingShowImage(for: show) {
            return showImageComedian
        }

        return ShowRow.artworkComedian(for: show)
    }

    private static func lineupComedianMatchingShowImage(for show: Components.Schemas.Show) -> Components.Schemas.ComedianLineup? {
        let showImageURL = show.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !showImageURL.isEmpty, let lineup = show.lineup else { return nil }

        return lineup
            .map(ShowRow.effectiveComedian)
            .first { comedian in
                comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines) == showImageURL
            }
    }
}
