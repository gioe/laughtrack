import Testing
import Foundation
import LaughTrackAPIClient
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Home content sections")
struct HomeContentSectionTests {
    @Test("unfiltered home leads with show rails before comedians and clubs")
    func unfilteredHomeLeadsWithShowRailsBeforeComediansAndClubs() {
        #expect(HomeContentSection.sections(for: nil) == [
            .showsTonight,
            .followedComedianShows,
            .thisWeek,
            .comedians,
            .clubs,
            .podcasts,
        ])
    }

    @Test("home primitive filters render only their matching content sections")
    func homePrimitiveFiltersRenderOnlyMatchingContentSection() {
        #expect(HomeContentSection.sections(for: .shows) == [
            .showsTonight,
            .followedComedianShows,
            .thisWeek,
        ])
        #expect(HomeContentSection.sections(for: .comedians) == [.comedians])
        #expect(HomeContentSection.sections(for: .clubs) == [.clubs])
        #expect(HomeContentSection.sections(for: .podcasts) == [.podcasts])
    }

    @Test("first viewport offers property-based discovery ideas")
    func firstViewportOffersPropertyBasedDiscoveryIdeas() {
        #expect(HomeDiscoveryIdea.allCases == [.tonight, .thisWeekend, .freeShows, .openMics])

        let nearby = NearbyPreference(
            zipCode: "10012",
            source: .manual,
            distanceMiles: 25
        )
        #expect(HomeDiscoveryIdea.tonight.searchSeed(nearbyPreference: nearby).shortcut == "Tonight")
        #expect(HomeDiscoveryIdea.thisWeekend.searchSeed(nearbyPreference: nearby).shortcut == "This Weekend")
        #expect(HomeDiscoveryIdea.freeShows.searchSeed(nearbyPreference: nearby).showSearch?.filterSlugs == ["free"])
        #expect(HomeDiscoveryIdea.openMics.searchSeed(nearbyPreference: nearby).showSearch?.filterSlugs == ["open_mic"])
    }

    @Test("discover section anchors retain the nearest section at the viewport top")
    func discoverSectionAnchorsRetainNearestSectionAtViewportTop() {
        #expect(HomeScrollRetention.visibleSection(from: [
            .showsTonight: -280,
            .followedComedianShows: -12,
            .thisWeek: 220,
        ]) == .followedComedianShows)
        #expect(HomeScrollRetention.restorableSection(
            .clubs,
            among: HomeContentSection.sections(for: nil)
        ) == .clubs)
        #expect(HomeScrollRetention.restorableSection(
            .clubs,
            among: HomeContentSection.sections(for: .shows)
        ) == .showsTonight)
    }

    @Test("expandable Discover rails expose See all and typed Search handoff")
    func expandableDiscoverRailsExposeSeeAllAndTypedSearchHandoff() throws {
        let source = try homeSourceText()

        #expect(source.contains("LaughTrackButton(\"See all\""))
        #expect(source.components(separatedBy: "actionTitle: \"See all\"").count - 1 == 3)
        #expect(source.contains(".discoverEntity(.comedians)"))
        #expect(source.contains("nearbyPreference: nearbyPreferenceStore.preference ?? nearbyPreferenceStore.defaultPreference"))
        #expect(source.contains(".discoverEntity(.podcasts)"))
        #expect(source.contains("HomeDiscoveryIdeas("))
        #expect(source.contains("ScrollViewReader"))
        #expect(source.contains("proxy.scrollTo(section, anchor: .top)"))
    }

    @Test("home show hero omits footer actions")
    func homeShowHeroOmitsFooterActions() {
        let show = Components.Schemas.Show(
            id: 801,
            clubId: 301,
            clubName: "Comedy In Harlem",
            date: Date(timeIntervalSince1970: 1_777_590_000),
            tickets: [.init(price: 0, purchaseUrl: "https://example.com/tickets", soldOut: false, _type: "General admission")],
            name: "K Smith & Friends",
            socialData: nil,
            lineup: [],
            description: nil,
            address: "750A St Nicholas Ave, New York, NY",
            room: nil,
            imageUrl: "",
            soldOut: false,
            distanceMiles: 10.6
        )

        #expect(HomeShowsTonightHeroPresentation.shouldShowFooter(for: show) == false)
    }

    @Test("home carousel claims horizontal swipes without treating vertical scrolls as paging")
    func homeCarouselClaimsHorizontalSwipesWithoutTreatingVerticalScrollsAsPaging() {
        #expect(HomeHorizontalPagerDrag.nextIndex(
            currentIndex: 0,
            itemCount: 3,
            pageWidth: 300,
            translation: CGSize(width: -90, height: 8)
        ) == 1)
        #expect(HomeHorizontalPagerDrag.nextIndex(
            currentIndex: 1,
            itemCount: 3,
            pageWidth: 300,
            translation: CGSize(width: 90, height: 8)
        ) == 0)
        #expect(HomeHorizontalPagerDrag.nextIndex(
            currentIndex: 1,
            itemCount: 3,
            pageWidth: 300,
            translation: CGSize(width: 40, height: 120)
        ) == 1)
        #expect(HomeHorizontalPagerDrag.nextIndex(
            currentIndex: 0,
            itemCount: 3,
            pageWidth: 300,
            translation: CGSize(width: 120, height: 8)
        ) == 0)
        #expect(HomeHorizontalPagerDrag.nextIndex(
            currentIndex: 2,
            itemCount: 3,
            pageWidth: 300,
            translation: CGSize(width: -120, height: 8)
        ) == 2)
        #expect(HomeHorizontalPagerDrag.nextIndex(
            currentIndex: 1,
            itemCount: 3,
            pageWidth: 300,
            translation: CGSize(width: 40, height: 8)
        ) == 1)
        #expect(HomeHorizontalPagerDrag.nextIndex(
            currentIndex: 0,
            itemCount: 0,
            pageWidth: 300,
            translation: CGSize(width: -120, height: 8)
        ) == 0)
    }

    @Test("tonight carousel keeps shared chrome outside moving show pages")
    func tonightCarouselKeepsSharedChromeOutsideMovingShowPages() throws {
        let source = try homeSourceText()
        let carouselBlock = try sourceBlock(
            in: source,
            from: "private struct HomeShowsTonightCarousel",
            to: "private struct HomeShowsTonightPageIndicator"
        )
        let heroBlock = try sourceBlock(
            in: source,
            from: "struct HomeShowsTonightHeroCard",
            to: "struct HomeShowsTonightPortraitMetrics"
        )
        let scrollingCardBlock = try sourceBlock(
            in: source,
            from: "private struct HomeShowsTonightScrollingCard",
            to: "struct HomeShowsTonightHeroCard"
        )

        #expect(carouselBlock.contains("Text(\"TONIGHT!\")"))
        #expect(carouselBlock.contains("HomeMarqueeStageBackground("))
        #expect(carouselBlock.contains("HomeShowsTonightPageIndicator("))
        #expect(carouselBlock.contains("scrollingCarouselButtons(cardWidth: 320)"))
        #expect(carouselBlock.contains(".background(laughTrack.colors.surface)"))
        #expect(carouselBlock.contains(".stroke(laughTrack.colors.borderSubtle"))
        #expect(scrollingCardBlock.contains("Text(\"TONIGHT!\")"))
        #expect(scrollingCardBlock.contains("HomeMarqueeStageBackground("))
        #expect(scrollingCardBlock.contains("HomeShowsTonightPageIndicator("))
        #expect(scrollingCardBlock.contains(".background(laughTrack.colors.surface)"))
        #expect(scrollingCardBlock.contains(".stroke(laughTrack.colors.borderSubtle"))
        #expect(heroBlock.contains("ClubWallHeadshotFrame("))
        #expect(heroBlock.contains("Text(timeLabel)"))
        #expect(heroBlock.contains("Text(ShowTitlePresentation.title(for: show))"))
        #expect(heroBlock.contains("Text(venueLine)"))
        #expect(!heroBlock.contains("Text(\"TONIGHT!\")"))
        #expect(!heroBlock.contains("HomeMarqueeStageBackground("))
        #expect(!heroBlock.contains("HomeShowsTonightPageIndicator("))
    }

    @Test("home cards use cached async images")
    func homeCardsUseCachedAsyncImages() throws {
        let source = try homeSourceText()

        #expect(!source.contains("\n            AsyncImage(url:"))
        #expect(source.contains("CachedAsyncImage(url:"))
    }

    @Test("home club cards fit club artwork without cropping")
    func homeClubCardsFitClubArtworkWithoutCropping() throws {
        let source = try homeSourceText()
        let block = try sourceBlock(
            in: source,
            from: "private struct HomePopularClubCard",
            to: "private var posterFallback: some View"
        )

        #expect(block.contains(".scaledToFit()"))
        #expect(!block.contains(".scaledToFill()"))
    }

    @Test("home podcast cards show podcast title without owner subtitle")
    func homePodcastCardsShowPodcastTitleWithoutOwnerSubtitle() throws {
        let source = try homeSourceText()
        let block = try sourceBlock(
            in: source,
            from: "private struct HomeTrendingPodcastCard",
            to: "@MainActor\nfinal class HomeTrendingPodcastsModel"
        )

        #expect(block.contains("Text(podcast.title)"))
        #expect(!block.contains("Text(subtitleText)"))
        #expect(!block.contains("podcast.authorName"))
        #expect(!block.contains("accessibilityLabel(\"\\(podcast.title),"))
    }

    @Test("home podcast cards use RSS badge artwork treatment")
    func homePodcastCardsUseRSSBadgeArtworkTreatment() throws {
        let source = try homeSourceText()
        let block = try sourceBlock(
            in: source,
            from: "private struct HomeTrendingPodcastCard",
            to: "@MainActor\nfinal class HomeTrendingPodcastsModel"
        )

        #expect(block.contains("private static let coverSize: CGFloat = 88"))
        #expect(block.contains("private static let coverCornerRadius: CGFloat = 8"))
        #expect(block.contains("private var podcastCover: some View"))
        #expect(block.contains("private var rssBadge: some View"))
        #expect(block.contains("private var waveformStrip: some View"))
        #expect(block.contains("Image(systemName: \"dot.radiowaves.left.and.right\")"))
        #expect(block.contains("Image(systemName: \"waveform\")"))
        #expect(block.contains(".overlay(alignment: .topTrailing)"))
        #expect(block.contains("rssBadge"))
        #expect(block.contains("ForEach(0..<9, id: \\.self)"))
        #expect(block.contains("height: CGFloat([7, 13, 9, 18, 11, 15, 8, 12, 6][index])"))
        #expect(block.contains("laughTrack.colors.accentStrong.opacity(0.92)"))
        #expect(block.contains("posterImage"))
        #expect(!block.contains("HomeBulbFrame("))
        #expect(!block.contains("vinylRecord"))
        #expect(!block.contains("recordSleeve"))
    }

    @Test("home source uses fixed-width carousel hero grid entity rails and lifted rail copy")
    func homeSourceUsesFixedWidthCarouselHeroGridEntityRailsAndLiftedRailCopy() throws {
        let source = try homeSourceText()
        let carouselBlock = try sourceBlock(
            in: source,
            from: "private struct HomeShowsTonightCarousel",
            to: "private struct HomeShowsTonightPageIndicator"
        )
        let heroBlock = try sourceBlock(
            in: source,
            from: "struct HomeShowsTonightHeroCard",
            to: "enum HomeShowsTonightHeroPresentation"
        )

        #expect(carouselBlock.contains("GeometryReader"))
        #expect(carouselBlock.contains("UIScreen.main.bounds.width - 64"))
        #expect(carouselBlock.contains(".frame(width: pageWidth"))
        #expect(carouselBlock.contains(".clipped()"))
        #expect(carouselBlock.contains(".frame(height: 456)"))
        #expect(carouselBlock.contains(".highPriorityGesture(pagerDragGesture(pageWidth: contentWidth))"))
        #expect(heroBlock.contains(".scaledToFill()"))
        #expect(source.contains("HomeDiscoverHeader("))
        #expect(source.contains("nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self)"))
        #expect(source.contains("profileLocationPreferenceSyncClient: serviceContainer.resolveOptional((any ProfileLocationPreferenceSyncing).self)"))
        #expect(source.contains("currentUser: authManager.currentUser"))
        #expect(source.contains("SettingsNearbyPreferenceModel("))
        #expect(source.contains("syncClient: profileLocationPreferenceSyncClient"))
        #expect(source.contains("refreshProfileLocation(from: currentUser)"))
        #expect(source.contains("HomeLocationPrompt("))
        #expect(source.contains("nearbyLocationController.preference ?? nearbyPreferenceStore.defaultPreference"))
        #expect(source.contains("HomeLocationEditorSheet("))
        #expect(source.contains("LazyVGrid"))
        #expect(source.contains("Best shows this week"))
        #expect(source.contains("return nil"))
        #expect(!source.contains("Shows tonight near"))
        #expect(!source.contains("return \"Shows tonight\""))
        #expect(!source.contains("Upcoming shows at clubs in your area."))
        #expect(!source.contains("The most popular shows happening in the next 7 days."))
        #expect(source.contains("Drawing Crowds"))
        #expect(source.contains("Popular local comedians"))
        #expect(source.contains("title: \"Popular local comedians\""))
        #expect(source.contains("subtitle: nil"))
        #expect(!source.contains("title: \"On the mic\""))
        #expect(!source.contains("eyebrow: \"Trending comedians\""))
        #expect(source.contains("ShowRow(show: show, presentation: .compactTicket)"))
    }

    @Test("discover page uses shared club-stage chrome beyond the tonight rail")
    func discoverPageUsesSharedClubStageChromeBeyondTheTonightRail() throws {
        let source = try homeSourceText()

        #expect(source.contains("struct LaughTrackAtmosphereBackground"))
        #expect(source.contains("struct HomeDiscoverRailCard"))
        #expect(source.contains("struct HomeMarqueeStageBackground"))
        #expect(source.contains("struct HomeBulbFrame"))
        #expect(source.contains("case spotlight"))
        #expect(source.contains("case scheduleBoard"))
        #expect(source.contains("variant: .posterGrid"))
        #expect(source.contains("variant: .listeningRoom"))
        #expect(source.contains(".modifier(LaughTrackNavigationChrome(background: .clear))"))
        #expect(source.contains("private let spotlightHue = Color(red: 1.0, green: 0.72, blue: 0.30)"))
        #expect(source.contains("center: .topLeading"))
        #expect(source.contains("Coming Up"))
        #expect(source.contains("Best shows this week"))
        #expect(source.contains("Drawing Crowds"))
        #expect(source.contains("Popular local comedians"))
        #expect(source.contains("Hot Rooms"))
        #expect(source.contains("Popular local clubs"))
        #expect(!source.contains("Rooms with heat"))
        #expect(!source.contains("subtitle: \"Popular clubs\""))
        #expect(source.contains("Funny listening"))
        #expect(source.contains("Popular comedy podcasts"))
        #expect(!source.contains("title: \"After hours\""))
        #expect(!source.contains("subtitle: \"Queue up the laughs\""))
    }

    @Test("discover location chip owns location copy for saved and feed default locations")
    func discoverLocationChipOwnsLocationCopyForSavedAndFeedDefaultLocations() throws {
        let source = try homeSourceText()
        let headerBlock = try sourceBlock(
            in: source,
            from: "private struct HomeDiscoverHeader",
            to: "struct HomeLocationPrompt"
        )
        let promptBlock = try sourceBlock(
            in: source,
            from: "struct HomeLocationPrompt",
            to: "struct HomeLocationEditorSheet"
        )
        let railBlock = try sourceBlock(
            in: source,
            from: "struct HomeShowsTonightRail",
            to: "private struct HomeShowsTonightCarousel"
        )

        #expect(headerBlock.contains("@ObservedObject private var nearbyPreferenceStore: NearbyPreferenceStore"))
        #expect(headerBlock.contains("displayPreference: nearbyLocationController.preference ?? nearbyPreferenceStore.defaultPreference"))
        #expect(promptBlock.contains("let displayPreference: NearbyPreference?"))
        #expect(promptBlock.contains("let isExplicitPreference: Bool"))
        #expect(promptBlock.contains("displayPreference == nil ? \"location.circle\" : \"location.fill\""))
        #expect(promptBlock.contains("guard let displayPreference else"))
        #expect(promptBlock.contains("if isExplicitPreference"))
        #expect(promptBlock.contains("return \"Default area - \\(displayPreference.distanceMiles) mi\""))
        #expect(!railBlock.contains("cityTitle"))
        #expect(!source.contains("Shows tonight near"))
    }

    @Test("discover location sheet uses compact form-first layout")
    func discoverLocationSheetUsesCompactFormFirstLayout() throws {
        let source = try homeSourceText()
        let block = try sourceBlock(
            in: source,
            from: "struct HomeLocationEditorSheet",
            to: "private func applyZip()"
        )

        #expect(block.contains("sheetHeader"))
        #expect(block.contains("zipControl"))
        #expect(block.contains("distanceControl"))
        #expect(block.contains("messageArea"))
        #expect(block.contains("actionStack"))
        #expect(block.contains(".presentationDetents([.height(430), .large])"))
        #expect(block.contains("Text(\"Choose where Discover looks for shows, clubs, and comedians.\")"))
        #expect(!block.contains("private static let pinIconSize"))
        #expect(!block.contains("pinWithFrame"))
        #expect(!block.contains("Text(\"Nearby\")"))
    }

    @Test("discover comedian cards use club wall framed headshots")
    func discoverComedianCardsUseClubWallFramedHeadshots() throws {
        let source = try homeSourceText()
        let block = try sourceBlock(
            in: source,
            from: "struct HomeTrendingComedianCard",
            to: "@MainActor\nfinal class HomeTrendingComediansModel"
        )

        #expect(block.contains("ClubWallHeadshotFrame("))
        #expect(block.contains("caption: comedian.name"))
        #expect(block.contains("GeometryReader"))
        #expect(block.contains("let metrics = headshotMetrics(for: proxy.size.width)"))
        #expect(block.contains("photoWidth: metrics.photoWidth"))
        #expect(block.contains("frameWidth: metrics.frameWidth"))
        #expect(block.contains("captionFontSize: metrics.captionFontSize"))
        #expect(block.contains("private func headshotMetrics(for availableWidth: CGFloat)"))
        #expect(block.contains("let widthScale = max(0.82, availableWidth / 156)"))
        #expect(block.contains("let heightScale = max(0.65, stageHeight / 154)"))
        #expect(block.contains("let scale = min(1.0, widthScale, heightScale)"))
        #expect(block.contains("photoWidth: 124 * scale"))
        #expect(block.contains("frameWidth: 144 * scale"))
        #expect(block.contains("frameHeight: 154 * scale"))
        #expect(block.contains("captionFontSize: 9.0 * scale"))
        #expect(block.contains("captionWidth: 116 * scale"))
        #expect(source.contains("ClubWallHeadshotFrame("))
        #expect(!block.contains("HomeBulbFrame("))
        #expect(!block.contains("Text(comedian.name)"))
        #expect(!block.contains("rotationDegrees:"))
        #expect(!block.contains(".background(laughTrack.colors.surface)"))
        #expect(!block.contains(".clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))"))
    }

    @Test("popular club cards use square art with warmer sparser bulb lights")
    func popularClubCardsUseSquareArtWithWarmerSparserBulbLights() throws {
        let source = try homeSourceText()
        let block = try sourceBlock(
            in: source,
            from: "private struct HomePopularClubCard",
            to: "@MainActor\nfinal class HomePopularClubsModel"
        )
        let bulbFrameBlock = try sourceBlock(
            in: source,
            from: "struct HomeBulbFrame",
            to: "private struct HomeDiscoverHeader"
        )

        #expect(block.contains("private static let posterCornerRadius: CGFloat = 8"))
        #expect(block.contains(".clipShape(RoundedRectangle(cornerRadius: Self.posterCornerRadius, style: .continuous))"))
        #expect(block.contains("RoundedRectangle(cornerRadius: Self.posterCornerRadius, style: .continuous)"))
        #expect(block.contains("cornerRadius: Self.posterCornerRadius + Self.posterFrameInset / 2"))
        #expect(block.contains("bulbColor: Self.clubBulbColor"))
        #expect(block.contains("dash: [1.2, 10]"))
        #expect(block.contains("private static let clubBulbColor = Color(red: 1.0, green: 0.78, blue: 0.24)"))
        #expect(!block.contains(".clipShape(Circle())"))
        #expect(!block.contains("isCircle: true"))
        #expect(bulbFrameBlock.contains("var bulbColor: Color? = nil"))
        #expect(bulbFrameBlock.contains("let resolvedBulbColor = bulbColor ?? laughTrack.colors.accentStrong"))
    }

    @Test("tonight hero artwork uses club wall framed headshot treatment")
    func tonightHeroArtworkUsesClubWallFramedHeadshotTreatment() throws {
        let source = try homeSourceText()
        let block = try sourceBlock(
            in: source,
            from: "struct HomeShowsTonightHeroCard",
            to: "enum HomeShowsTonightHeroPresentation"
        )

        #expect(block.contains("ClubWallHeadshotFrame("))
        #expect(block.contains("caption: headshotCaption"))
        #expect(block.contains("GeometryReader"))
        #expect(block.contains("let metrics = portraitMetrics("))
        #expect(block.contains("artworkHeight: artworkHeight"))
        #expect(block.contains("private func portraitMetrics("))
        #expect(block.contains("let widthScale = max(0.84, availableWidth / 300)"))
        #expect(block.contains("let heightScale = max(0.72, artworkHeight / 170)"))
        #expect(block.contains("photoWidth: 138 * scale"))
        #expect(block.contains("frameWidth: 154 * scale"))
        #expect(block.contains("frameHeight: 170 * scale"))
        #expect(block.contains("captionWidth: 126 * scale"))
        #expect(block.contains("photoWidth: metrics.photoWidth"))
        #expect(block.contains("frameWidth: metrics.frameWidth"))
        #expect(block.contains("captionFontSize: metrics.captionFontSize"))
        #expect(block.contains("private var headshotCaption: String"))
        #expect(!block.contains("rotationDegrees:"))
        #expect(!block.contains("HomeBulbFrame("))
    }

    @Test("tonight hero keeps the headshot nameplate prominent while reducing show metadata")
    func tonightHeroKeepsTheHeadshotNameplateProminentWhileReducingShowMetadata() throws {
        let source = try homeSourceText()
        let block = try sourceBlock(
            in: source,
            from: "struct HomeShowsTonightHeroCard",
            to: "enum HomeShowsTonightHeroPresentation"
        )

        #expect(block.contains(".font(.system(size: 30, weight: .heavy, design: .rounded))"))
        #expect(block.contains(".font(.system(size: 16, weight: .heavy, design: .rounded))"))
        #expect(block.contains(".font(.system(size: 9, weight: .semibold, design: .rounded))"))
        #expect(block.contains(".padding(.horizontal, 12)"))
        #expect(block.contains(".padding(.vertical, 5)"))
        #expect(!block.contains("HomeShowsTonightPageIndicator("))
        #expect(!block.contains("pageIndicatorCount"))
        #expect(!block.contains("selectedPageIndex"))
    }

    @Test("tonight hero caption follows the comedian used for artwork")
    func tonightHeroCaptionFollowsTheComedianUsedForArtwork() {
        let mikeImage = "https://cdn.example.com/mike-britt.jpg"
        let show = Components.Schemas.Show(
            id: 902,
            clubId: 301,
            clubName: "New York Comedy Club East Village",
            date: Date(timeIntervalSince1970: 1_777_590_000),
            tickets: [],
            name: "Josh Johnson, Mike Britt, Brittany Brave",
            socialData: nil,
            lineup: [
                .init(
                    name: "Brittany Brave",
                    imageUrl: "https://cdn.example.com/brittany-brave.jpg",
                    uuid: "brittany-brave",
                    id: 11,
                    userId: nil,
                    socialData: .init(id: 11, popularity: 90),
                    isFavorite: false,
                    showCount: 2
                ),
                .init(
                    name: "Mike Britt",
                    imageUrl: mikeImage,
                    uuid: "mike-britt",
                    id: 12,
                    userId: nil,
                    socialData: .init(id: 12, popularity: 10),
                    isFavorite: false,
                    showCount: 19
                ),
            ],
            description: nil,
            address: "85 E 4th St, New York, NY",
            room: nil,
            imageUrl: mikeImage,
            soldOut: false,
            distanceMiles: nil
        )

        #expect(HomeShowsTonightHeroPresentation.headshotCaption(for: show) == "Brittany Brave")
        #expect(
            HomeShowsTonightHeroPresentation.artworkImageURL(for: show)
                == "https://cdn.example.com/brittany-brave.jpg"
        )
    }

    // The Home surface was split out of the single HomeView.swift (TASK-3641)
    // into Home/Models and Home/Views/Rails. Source-inspection assertions read
    // the concatenation of every Home source file; the order interleaves each
    // rail with its model so pre-split block markers (card -> model) still
    // resolve across what are now file boundaries.
    private func homeSourceText(filePath: String = #filePath) throws -> String {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let homeRoot = iosRoot.appendingPathComponent("Sources/LaughTrackApp/Home")
        let relativePaths = [
            "Views/Rails/HomeRailChrome.swift",
            "Views/HomeView.swift",
            "Views/HomeLocationEditor.swift",
            "Views/Rails/HomeShowsTonightRail.swift",
            "Models/HomeShowsTonightModel.swift",
            "Models/HomeFavoriteShowsModel.swift",
            "Views/Rails/HomeFollowedComedianShowsRail.swift",
            "Views/Rails/HomeTrendingComediansRail.swift",
            "Models/HomeTrendingComediansModel.swift",
            "Views/Rails/HomePopularClubsRail.swift",
            "Models/HomePopularClubsModel.swift",
            "Views/Rails/HomeTrendingPodcastsRail.swift",
            "Models/HomeTrendingPodcastsModel.swift",
            "Models/MainPageCache.swift",
            "Models/HomeFeedRequestCoalescer.swift",
            "Components/SessionBannerCard.swift",
        ]
        // Guard against silent drift: a Swift file added under Home/ that is
        // missing from the ordered list above would otherwise escape every
        // whole-source negative assertion in this suite.
        let enumerated = try FileManager.default
            .subpathsOfDirectory(atPath: homeRoot.path)
            .filter { $0.hasSuffix(".swift") }
        guard Set(enumerated) == Set(relativePaths) else {
            throw CocoaError(.fileReadCorruptFile)
        }
        var combined = ""
        for relative in relativePaths {
            let url = homeRoot.appendingPathComponent(relative)
            guard FileManager.default.fileExists(atPath: url.path) else {
                throw CocoaError(.fileNoSuchFile)
            }
            combined += try String(contentsOf: url, encoding: .utf8) + "\n"
        }
        return combined
    }

    private func sourceBlock(in source: String, from startMarker: String, to endMarker: String) throws -> String {
        guard
            let start = source.range(of: startMarker),
            let end = source.range(of: endMarker, range: start.upperBound..<source.endIndex)
        else {
            throw CocoaError(.fileReadCorruptFile)
        }

        return String(source[start.lowerBound..<end.lowerBound])
    }
}
