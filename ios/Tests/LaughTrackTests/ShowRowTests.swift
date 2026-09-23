import Foundation
import Testing
import SwiftUI
import Combine
import LaughTrackAPIClient
import LaughTrackBridge
@testable import LaughTrackApp

#if canImport(UIKit)
import UIKit

@Suite("Search agenda visual capture", .serialized)
@MainActor
struct SearchAgendaVisualTests {
    @Test("review dedicated and contextual lineups in mixed phone and tablet lists")
    func captureLineupCards() async throws {
        let primary = SearchAgendaFixtures.comedian("J Valentino")
        let luz = SearchAgendaFixtures.comedian("Luz Pazos", id: 2)
        var dwayne = SearchAgendaFixtures.comedian("Dwayne Perkins", id: 3)
        dwayne.imageUrl = ""
        let ensemble = SearchAgendaFixtures.show("COMEDY MADNESS (Dwayne Perkins, J Valentino, Luz Pazos, Michael Quu)", lineup: [primary, luz, dwayne])
        let solo = SearchAgendaFixtures.show("An Evening of Comedy", id: 2, lineup: [dwayne], price: 0)
        let unknown = SearchAgendaFixtures.show("New Material Night", id: 3, lineup: nil, price: nil)
        let long = SearchAgendaFixtures.show("A wonderfully long comedy showcase with stories from every corner of the city", id: 4,
            lineup: [SearchAgendaFixtures.comedian("A Performer With A Wonderfully Long Stage Name", id: 5)] + (6...10).map { SearchAgendaFixtures.comedian("Comic \($0)", id: $0) }, soldOut: true)
        let rows: [(Components.Schemas.Show, ShowRowPerformerContext?)] = [
            (ensemble, nil), (ensemble, .searchMatch(primary.id)), (solo, .followed(dwayne.id)), (unknown, nil), (long, nil), (ensemble, .followed(primary.id))
        ]
        for width in [CGFloat(375), CGFloat(834)] {
            for size in [DynamicTypeSize.large, .accessibility5] {
                let scroll = PassthroughSubject<Int, Never>()
                let host = HostedView(
                    ScrollViewReader { proxy in
                        ScrollView {
                            VStack(alignment: .leading, spacing: 16) {
                                Text("Shows").font(.title.bold())
                                AdaptiveSearchResults(spacing: 16) {
                                    ForEach(rows.indices, id: \.self) { index in
                                        ShowRow(show: rows[index].0, presentation: .compactTicket, context: index == 5 ? .standalone : .agenda, performerContext: rows[index].1)
                                            .id(index)
                                    }
                                }
                            }.padding(16)
                        }.onReceive(scroll) { proxy.scrollTo($0, anchor: .top) }
                    }
                    .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
                    .environment(\.appTheme, LaughTrackTheme())
                    .environment(\.dynamicTypeSize, size)
                    .environment(\.horizontalSizeClass, width < 600 ? .compact : .regular)
                    .environmentObject(TypedNavigationCoordinator<AppRoute>())
                    .preferredColorScheme(.dark), freshWindow: true,
                    viewportSize: CGSize(width: width, height: width < 500 ? 1000 : 1194)
                )
                await host.settle()
                for index in rows.indices {
                    scroll.send(index)
                    await host.settle(iterations: 4)
                    let data = try #require(try host.snapshot().pngData())
                    let name = "task4039-\(Int(width))-\(size.isAccessibilitySize ? "AX5" : "standard")-row\(index).png"
                    let path = FileManager.default.temporaryDirectory.appendingPathComponent(name)
                    try data.write(to: path)
                    print("Lineup capture: \(path.path)")
                    #if compiler(>=6.2)
                    Attachment.record(Array(data), named: name)
                    #endif
                }
                let treePath = FileManager.default.temporaryDirectory.appendingPathComponent("task4039-\(Int(width))-\(size.isAccessibilitySize ? "AX5" : "standard")-accessibility.txt")
                host.dumpAccessibilityTree(writingTo: treePath.path)
                print("Lineup accessibility: \(treePath.path)")
            }
        }
    }

    @Test("capture agenda identities and ticket states at standard and accessibility sizes")
    func captureAgendaRows() async throws {
        for size in [DynamicTypeSize.large, .accessibility5] {
            for (name, shows) in SearchAgendaFixtures.captureCases {
                let scrollToBottom = PassthroughSubject<Void, Never>()
                let host = HostedView(
                    ScrollViewReader { proxy in
                        ScrollView {
                            VStack(alignment: .leading, spacing: 16) {
                                Text(name == "standalone" ? "Standalone ticket" : "Wednesday, September 16")
                                    .font(LaughTrackTheme().laughTrackTokens.typography.sectionTitle)
                                    .foregroundStyle(LaughTrackTheme().laughTrackTokens.colors.textPrimary)
                                AdaptiveSearchResults(spacing: 16) {
                                    ForEach(shows, id: \.id) { show in
                                        ShowRow(show: show, presentation: .compactTicket,
                                                context: name == "standalone" ? .standalone : .agenda)
                                    }
                                }
                                Color.clear.frame(height: 1).id("capture-bottom")
                            }
                            .padding(16)
                        }
                        .onReceive(scrollToBottom) { _ in
                            proxy.scrollTo("capture-bottom", anchor: .bottom)
                        }
                    }
                    .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
                    .environment(\.appTheme, LaughTrackTheme())
                    .environment(\.dynamicTypeSize, size)
                    .environmentObject(TypedNavigationCoordinator<AppRoute>())
                    .preferredColorScheme(.dark), freshWindow: true
                )
                await host.settle()
                let data = try #require(try host.snapshot().pngData())
                let textSize = size.isAccessibilitySize ? "AX5" : "standard"
                let path = FileManager.default.temporaryDirectory.appendingPathComponent("task4005-\(name)-\(textSize).png")
                try data.write(to: path)
                print("Search agenda capture: \(path.path)")
                #if compiler(>=6.2)
                Attachment.record(Array(data), named: path.lastPathComponent)
                #endif
                if size.isAccessibilitySize && name != "overview" && name != "standalone" {
                    scrollToBottom.send(())
                    await host.settle()
                    let bottomData = try #require(try host.snapshot().pngData())
                    let bottomPath = FileManager.default.temporaryDirectory.appendingPathComponent("task4005-\(name)-AX5-bottom.png")
                    try bottomData.write(to: bottomPath)
                    print("Search agenda capture: \(bottomPath.path)")
                    #if compiler(>=6.2)
                    Attachment.record(Array(bottomData), named: bottomPath.lastPathComponent)
                    #endif
                }
            }
        }
    }
}
#endif

private enum SearchAgendaFixtures {
    static func comedian(_ name: String, id: Int = 1, parent: Components.Schemas.ComedianLineup? = nil) -> Components.Schemas.ComedianLineup {
        .init(name: name, imageUrl: "https://example.invalid/comedian.png", uuid: "agenda-\(id)", id: id, showCount: 10, parentComedian: parent)
    }

    static func show(
        _ title: String = "Taylor Tomlinson",
        id: Int = 1,
        lineup: [Components.Schemas.ComedianLineup]? = [comedian("Taylor Tomlinson")],
        room: String? = "Main Room",
        price: Double? = 35,
        soldOut: Bool = false
    ) -> Components.Schemas.Show {
        .init(
            id: id, clubId: 201, clubName: "Comedy Cellar", clubCity: "New York", clubState: "NY",
            date: Date(timeIntervalSince1970: 1_789_603_200),
            tickets: [.init(price: price, purchaseUrl: "https://example.invalid/tickets", soldOut: soldOut, _type: "General admission")],
            name: title, lineup: lineup, room: room, imageUrl: "", soldOut: soldOut, timezone: "America/New_York"
        )
    }

    static var captureCases: [(String, [Components.Schemas.Show])] {
        let solo = show()
        let ensemble = show("Late Night Showcase", id: 2, lineup: [comedian("Sam Jay"), comedian("Ali Wong", id: 2), comedian("Atsuko Okatsuka", id: 3)], room: "Village Underground")
        let longTitle = show("A wonderfully long comedy showcase with stories from every corner of the city and special guests all evening", id: 3, lineup: nil, room: "The Upstairs Listening Room")
        let soldOut = show("Sold Out Saturday Showcase", id: 4, soldOut: true)
        let unknown = show("New Material Night", id: 5, lineup: nil, price: nil)
        return [("overview", [solo, ensemble, longTitle, soldOut, unknown]), ("solo", [solo]), ("ensemble", [ensemble]), ("long-title", [longTitle]), ("sold-out", [soldOut]), ("unknown-price", [unknown]), ("standalone", [solo])]
    }
}

@Suite("Show row")
@MainActor
struct ShowRowTests {
    @Test("show row exposes a compact paper ticket presentation for home rails")
    func showRowExposesCompactPaperTicketPresentationForHomeRails() throws {
        let source = try String(contentsOf: showRowSourceURL(), encoding: .utf8)

        #expect(source.contains("enum ShowRowPresentation"))
        #expect(source.contains("case standard"))
        #expect(source.contains("case compactTicket"))
        #expect(source.contains("case compactTicketProminent"))
        #expect(source.contains("let presentation: ShowRowPresentation"))
        #expect(source.contains("presentation: ShowRowPresentation = .standard"))
        #expect(source.contains("private var ticketPaper"))
        #expect(source.contains("private var ticketInk"))
        #expect(source.contains("private var ticketInkMuted"))
        #expect(source.contains("private var ticketBorder"))
        #expect(source.contains("private var ticketStubBackground"))
        #expect(source.contains("private var ticketEdgeAccent"))
        #expect(source.contains("case .compactTicket"))
    }

    @Test("show row does not render proximity badges")
    func showRowDoesNotRenderProximityBadges() throws {
        let source = try String(contentsOf: showRowSourceURL(), encoding: .utf8)

        #expect(!source.contains("Near you"))
        #expect(!source.contains("nearbyRadiusMiles"))
    }

    @Test("show row prefers lineup popularity over historical show count for artwork")
    func showRowUsesMostPopularLineupComedianImage() {
        let show = makeShow(lineup: [
            lineup(name: "Opening comic", imageURL: "https://example.com/opening.jpg", showCount: 120, popularity: 12),
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 4, popularity: 95),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 20, popularity: 30),
        ])

        #expect(ShowRow.artworkImageURL(for: show) == "https://example.com/headliner.jpg")
    }

    @Test("preferred headliner overrides the normal artwork ranking")
    func preferredHeadlinerOverridesArtworkRanking() {
        let usualHeadliner = lineup(
            name: "Usual Headliner",
            imageURL: "https://example.com/usual.jpg",
            showCount: 100,
            popularity: 100
        )
        let visitingComedian = lineup(
            name: "Visiting Comedian",
            imageURL: "https://example.com/visitor.jpg",
            showCount: 2,
            popularity: 2
        )
        let show = makeShow(lineup: [usualHeadliner, visitingComedian])

        #expect(
            ShowRow.artworkComedian(
                for: show,
                preferredComedianID: visitingComedian.id
            )?.name == "Visiting Comedian"
        )
        #expect(
            ShowRow.artworkImageURL(
                for: show,
                preferredComedianID: visitingComedian.id
            ) == "https://example.com/visitor.jpg"
        )
    }

    @Test("preferred canonical headliner resolves through a lineup alias")
    func preferredCanonicalHeadlinerResolvesAlias() {
        let canonical = lineup(
            name: "Canonical Visitor",
            imageURL: "https://example.com/canonical.jpg",
            showCount: 2
        )
        let alias = lineup(
            name: "Visitor Alias",
            imageURL: "https://example.com/alias.jpg",
            showCount: 2,
            parentComedian: canonical
        )
        let show = makeShow(lineup: [alias])

        #expect(
            ShowRow.artworkComedian(
                for: show,
                preferredComedianID: canonical.id
            )?.name == "Canonical Visitor"
        )
    }

    // Title-transformation behavior (plain passthrough, solo-headliner "<Performer>
    // Headlines", performer-looking fallback, named-show preservation) is owned by
    // ShowTitlePresentationTests — the single authoritative suite. ShowRow.title is a
    // thin passthrough, so we assert delegation rather than re-encoding the expected
    // strings here (see TASK-2537).
    @Test("show row title delegates to ShowTitlePresentation")
    func showRowTitleDelegatesToPresentation() {
        let show = makeShow(
            name: "Vanessa Jackson",
            clubName: "The Broadway Comedy Club",
            lineup: [
                lineup(name: "Vanessa Jackson", imageURL: "https://example.com/vanessa.jpg", showCount: 4)
            ]
        )

        #expect(ShowRow.title(for: show) == ShowTitlePresentation.title(for: show))
    }

    @Test("show row list title passes non-venue titles through unchanged")
    func showRowListTitlePassesThroughNonVenueTitles() {
        let show = makeShow(
            name: "Vanessa Jackson",
            clubName: "The Broadway Comedy Club",
            lineup: [
                lineup(name: "Vanessa Jackson", imageURL: "https://example.com/vanessa.jpg", showCount: 4)
            ]
        )

        // listTitle only collapses the "Comedy Show at <club>" venue fallback;
        // every other title (headline titles included) is passed through verbatim.
        #expect(ShowRow.listTitle(for: show) == ShowTitlePresentation.title(for: show))
    }

    @Test("show row collapses the venue fallback title in the compact list title")
    func showRowCollapsesVenueFallbackInCompactListTitle() {
        let show = makeShow(
            name: "",
            clubName: "The Broadway Comedy Club",
            lineup: nil
        )

        // The venue-fallback title itself is covered in ShowTitlePresentationTests;
        // here we assert ShowRow's own collapse of that fallback to "Comedy show".
        #expect(ShowRow.listTitle(for: show) == "Comedy show")
    }

    @Test("show row keeps named shows in compact list title")
    func showRowKeepsNamedShowsInCompactListTitle() {
        let show = makeShow(
            name: "Golden Gate Comedy Night",
            clubName: "The Function SF",
            lineup: nil
        )

        #expect(ShowRow.listTitle(for: show) == "Golden Gate Comedy Night")
    }

    @Test("artwork-backed rows preserve distinct event titles for the same headliner")
    func artworkBackedRowsPreserveDistinctEventTitlesForSameHeadliner() {
        let sharedHeadliner = lineup(
            name: "Shared Headliner",
            imageURL: "https://example.com/shared-headliner.jpg",
            showCount: 42
        )
        let fridayShow = makeShow(
            name: "Friday Night Showcase",
            lineup: [sharedHeadliner]
        )
        let saturdayShow = makeShow(
            name: "Saturday Night Showcase",
            lineup: [sharedHeadliner]
        )

        #expect(ShowRow.primaryListTitle(for: fridayShow, headliner: sharedHeadliner) == "Friday Night Showcase")
        #expect(ShowRow.primaryListTitle(for: saturdayShow, headliner: sharedHeadliner) == "Saturday Night Showcase")
        #expect(ShowRow.headlinerContext(for: fridayShow, headliner: sharedHeadliner) == "Shared Headliner")
        #expect(ShowRow.headlinerContext(for: saturdayShow, headliner: sharedHeadliner) == "Shared Headliner")
    }

    @Test("artwork-backed rows keep the performer primary for unnamed shows")
    func artworkBackedRowsKeepPerformerPrimaryForUnnamedShows() {
        let headliner = lineup(
            name: "Featured Comic",
            imageURL: "https://example.com/featured-comic.jpg",
            showCount: 20
        )
        let show = makeShow(name: "", clubName: "", lineup: [headliner])

        #expect(ShowRow.primaryListTitle(for: show, headliner: headliner) == "Featured Comic")
        #expect(ShowRow.headlinerContext(for: show, headliner: headliner) == nil)
    }

    @Test("artwork-backed rows keep the performer primary for venue-fallback shows")
    func artworkBackedRowsKeepPerformerPrimaryForVenueFallbackShows() {
        let headliner = lineup(
            name: "Featured Comic",
            imageURL: "https://example.com/featured-comic.jpg",
            showCount: 20
        )
        let show = makeShow(
            name: "",
            clubName: "The Broadway Comedy Club",
            lineup: [headliner]
        )

        #expect(ShowRow.listTitle(for: show) == "Comedy show")
        #expect(ShowRow.primaryListTitle(for: show, headliner: headliner) == "Featured Comic")
        #expect(ShowRow.headlinerContext(for: show, headliner: headliner) == nil)
        #expect(ShowRow.venueLine(for: show) == "The Broadway Comedy Club")
    }

    @Test("cards preserve supplied titles without inferring a billing role")
    func cardTitlesPreserveEventIdentity() {
        let performer = lineup(name: "J Valentino", imageURL: "", showCount: 1)
        let title = "COMEDY MADNESS (Dwayne Perkins, J Valentino, Luz Pazos, Michael Quu)"
        #expect(ShowRow.cardTitle(for: makeShow(name: title, lineup: [performer])) == title)
        #expect(ShowRow.cardTitle(for: makeShow(name: performer.name, lineup: [performer])) == performer.name)
        #expect(ShowRow.cardTitle(for: makeShow(name: "", lineup: [performer])) == "Comedy show")
    }

    @Test("performer-led cards require explicit context identifying a listed canonical performer")
    func contextualCardsValidateIdentity() {
        let canonical = lineup(name: "Canonical", imageURL: "", showCount: 1)
        let alias = lineup(name: "Alias", imageURL: "", showCount: 1, parentComedian: canonical)
        let show = makeShow(lineup: [alias])
        #expect(ShowRow.contextualComedian(for: show, context: nil) == nil)
        #expect(ShowRow.contextualComedian(for: show, context: .followed(-1)) == nil)
        #expect(ShowRow.contextualComedian(for: show, context: .searchMatch(alias.id)) == nil)
        #expect(ShowRow.contextualComedian(for: show, context: .searchMatch(canonical.id))?.name == canonical.name)
        #expect(ShowRow.contextualComedian(for: show, context: .followed(canonical.id))?.id == canonical.id)
        #expect(ShowRowPerformerContext.followed(canonical.id).reason == "You follow")
        #expect(ShowRowPerformerContext.searchMatch(canonical.id).reason == "Matches your comedian search")
    }

    @Test("missing and invalid photos never remove structured lineup names")
    func rosterSurvivesMissingArtwork() {
        for url in ["", "/placeholder.svg", "invalid", "https://example.invalid/fails.png"] {
            let comic = lineup(name: "Still on the lineup", imageURL: url, showCount: 1)
            let show = makeShow(lineup: [comic])
            #expect(ShowRow.lineupPortraitComedian(for: show)?.name == comic.name)
            #expect(ShowRow.lineupPreview(for: ShowRow.topLineup(for: show)) == comic.name)
        }
        #expect(ShowRow.lineupPortraitComedian(for: makeShow(lineup: nil)) == nil)
        #expect(ShowRow.lineupPortraitComedian(for: makeShow(lineup: [])) == nil)
    }

    @Test("canonical aliases count once in the portrait and overflow roster")
    func canonicalRosterDeduplicatesBeforeCounting() {
        let canonical = lineup(name: "Canonical", imageURL: "", showCount: 1)
        let alias = lineup(name: "Alias", imageURL: "", showCount: 1, parentComedian: canonical)
        let others = (1...4).map { lineup(name: "Comic \($0)", imageURL: "", showCount: 1) }
        let show = makeShow(lineup: [alias, canonical] + others)
        let roster = ShowRow.topLineup(for: show, limit: .max)
        #expect(roster.count == 5)
        #expect(ShowRow.lineupPreview(for: [alias, canonical] + others) == "Canonical, Comic 1, Comic 2 · +2 more")
        #expect(ShowRow.supportingLineup(for: show, excluding: canonical).count == 4)
    }

    @Test("show row venue line includes city and state when available")
    func showRowVenueLineIncludesCityAndState() {
        let show = makeShow(
            clubName: "The Grisly Pear Greenwich Village",
            clubCity: "New York",
            clubState: "NY",
            lineup: []
        )

        #expect(ShowRow.venueLine(for: show) == "The Grisly Pear Greenwich Village • New York, NY")
    }

    @Test("show row venue line falls back to club name without location")
    func showRowVenueLineFallsBackToClubNameWithoutLocation() {
        let show = makeShow(
            clubName: "The Grisly Pear Greenwich Village",
            clubCity: nil,
            clubState: nil,
            lineup: []
        )

        #expect(ShowRow.venueLine(for: show) == "The Grisly Pear Greenwich Village")
    }

    @Test("show row preserves longer production titles")
    func showRowPreservesLongerProductionTitles() {
        let show = makeShow(
            name: "Comedy Show at The Grisly Pear Midtown",
            clubName: "The Grisly Pear Midtown",
            lineup: nil
        )

        #expect(ShowRow.title(for: show) == "Comedy Show at The Grisly Pear Midtown")
    }

    @Test("show row keeps parent comedian artwork for alias lineup items")
    func showRowUsesParentComedianForAliasArtwork() {
        let parent = lineup(
            name: "Parent Headliner",
            imageURL: "https://example.com/parent.jpg",
            showCount: 5,
            popularity: 90
        )
        let alias = lineup(
            name: "Alias Name",
            imageURL: "https://example.com/alias.jpg",
            showCount: 50,
            popularity: 1,
            parentComedian: parent
        )
        let other = lineup(
            name: "Other Comic",
            imageURL: "https://example.com/other.jpg",
            showCount: 80,
            popularity: 40
        )
        let show = makeShow(lineup: [alias, other])

        #expect(ShowRow.title(for: show) == "Late show")
        #expect(ShowRow.artworkImageURL(for: show) == "https://example.com/parent.jpg")
    }

    @Test("show row falls back to absolute show artwork when lineup is empty")
    func showRowFallsBackToTicketArtworkWhenLineupIsEmpty() {
        let show = makeShow(lineup: [])

        #expect(ShowRow.artworkImageURL(for: show) == "https://example.com/show.jpg")
    }

    @Test("show row ignores relative show artwork placeholders")
    func showRowIgnoresRelativeShowArtworkPlaceholders() {
        let show = makeShow(imageURL: "/placeholders/club-placeholder.svg", lineup: [])

        #expect(ShowRow.artworkImageURL(for: show) == nil)
    }

    @Test("show row uses a stable branded artwork slot")
    func showRowUsesStableBrandedArtworkSlot() throws {
        let source = try String(contentsOf: showRowSourceURL(), encoding: .utf8)

        #expect(ShowRow.artworkSlotSize == 60)
        #expect(source.contains("private func portrait(for comedian:"))
        #expect(source.contains("Image(systemName: ArtworkFallbackKind.person.systemImage)"))
        #expect(source.components(separatedBy: "artworkSlot").count >= 4)
    }

    @Test("show row uses the first lineup image when popularity counts are absent")
    func showRowUsesFirstLineupImageWhenPopularityCountsAreAbsent() {
        let show = makeShow(lineup: [
            lineup(name: "First comic", imageURL: "https://example.com/first.jpg", showCount: nil),
            lineup(name: "Second comic", imageURL: "https://example.com/second.jpg", showCount: nil),
        ])

        #expect(ShowRow.artworkImageURL(for: show) == "https://example.com/first.jpg")
    }

    @Test("list dates use the supplied venue timezone")
    func listDatesUseSuppliedVenueTimezone() {
        let date = Date(timeIntervalSince1970: 1_714_780_800)

        #expect(ShowFormatting.listDate(date, timezoneID: "America/New_York").contains("8:00"))
        #expect(ShowFormatting.listDate(date, timezoneID: "America/Los_Angeles").contains("5:00"))
    }

    @Test("date stack returns weekday, day, and time in the venue timezone")
    func dateStackReturnsComponentsInVenueTimezone() {
        // 2024-05-04 00:00:00 UTC → 2024-05-03 20:00 ET → Friday the 3rd
        let date = Date(timeIntervalSince1970: 1_714_780_800)
        let stack = ShowFormatting.dateStack(date, timezoneID: "America/New_York")

        #expect(stack.weekday == "FRI")
        #expect(stack.day == "3")
        #expect(stack.time.contains("8:00"))
    }

    @Test("date stack appends timezone abbreviation when venue timezone differs from device timezone")
    func dateStackAppendsRemoteTimezoneAbbreviation() {
        let date = Date(timeIntervalSince1970: 1_714_780_800)
        let stack = ShowFormatting.dateStack(
            date,
            timezoneID: "America/Los_Angeles",
            localTimezone: TimeZone(identifier: "America/New_York")!
        )

        #expect(stack.time.contains("5:00"))
        #expect(stack.time.contains("PDT"))
    }

    @Test("date stack omits timezone abbreviation when venue timezone matches device timezone")
    func dateStackOmitsLocalTimezoneAbbreviation() {
        let date = Date(timeIntervalSince1970: 1_714_780_800)
        let stack = ShowFormatting.dateStack(
            date,
            timezoneID: "America/New_York",
            localTimezone: TimeZone(identifier: "America/New_York")!
        )

        #expect(stack.time.contains("8:00"))
        #expect(!stack.time.contains("EDT"))
    }

    @Test("featured date and time includes the venue date and timestamp")
    func featuredDateAndTimeIncludesVenueDateAndTimestamp() {
        let date = Date(timeIntervalSince1970: 1_714_780_800)
        let label = ShowFormatting.featuredDateTime(
            date,
            timezoneID: "America/Los_Angeles",
            localTimezone: TimeZone(identifier: "America/New_York")!
        )

        #expect(label.replacingOccurrences(of: "\u{202F}", with: " ") == "FRI, MAY 3 • 5:00 PM PDT")
    }

    @Test("open mic detection reads the tag list without depending on the show name")
    func openMicDetection() {
        // Deliberately use a non-open-mic name so this asserts the tag-based
        // path, not the name-string fallback. ShowRow + ShowDetailView are
        // driven by the same signal.
        let openMic = makeShow(
            name: "Late Set",
            tags: [.init(slug: "open-mic", name: "Open Mic")],
            lineup: nil
        )
        #expect(ShowRow.isOpenMic(openMic))

        let nonOpenMic = makeShow(
            name: "Late Set",
            tags: [.init(slug: "weekly-showcase", name: "Weekly Showcase")],
            lineup: nil
        )
        #expect(ShowRow.isOpenMic(nonOpenMic) == false)

        let untagged = makeShow(name: "Late Set", tags: nil, lineup: nil)
        #expect(ShowRow.isOpenMic(untagged) == false)
    }

    @Test("name-based open mic fallback still recognizes common name variants")
    func openMicNameFallback() {
        // Defensive fallback for venues whose tag list hasn't been backfilled
        // yet — the function is intentionally retained on ShowFormatting.
        #expect(ShowFormatting.isOpenMic("Tuesday Open Mic"))
        #expect(ShowFormatting.isOpenMic("OPEN MIC"))
        #expect(ShowFormatting.isOpenMic("Comedy open-mic night"))
        #expect(ShowFormatting.isOpenMic("Atsuko Late Set") == false)
        #expect(ShowFormatting.isOpenMic(nil) == false)
    }

    @Test("top lineup ranks by popularity, then show count, then lineup order")
    func topLineupPicksMostPopular() {
        let show = makeShow(lineup: [
            lineup(name: "Opener", imageURL: "https://example.com/opener.jpg", showCount: 3, popularity: 20),
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 2, popularity: 90),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 20, popularity: 20),
            lineup(name: "Filler", imageURL: "https://example.com/filler.jpg", showCount: 20, popularity: 20),
        ])

        let top = ShowRow.topLineup(for: show)

        #expect(top.map(\.name) == ["Headliner", "Feature", "Filler"])
    }

    @Test("top lineup excludes the artwork comedian to avoid duplicate avatars")
    func topLineupExcludesArtworkComedian() {
        let show = makeShow(lineup: [
            lineup(name: "Opener", imageURL: "https://example.com/opener.jpg", showCount: 3),
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 42),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 20),
            lineup(name: "Filler", imageURL: "https://example.com/filler.jpg", showCount: 1),
        ])

        let artwork = ShowRow.artworkComedian(for: show)
        #expect(artwork?.name == "Headliner")
        #expect(ShowRow.topLineup(for: show, excluding: artwork).map(\.name) == ["Feature", "Opener", "Filler"])
    }

    @Test("supporting lineup preserves performers beyond the three-avatar limit")
    func supportingLineupPreservesOverflowPerformers() {
        let show = makeShow(lineup: [
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 50),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 40),
            lineup(name: "Opener", imageURL: "https://example.com/opener.jpg", showCount: 30),
            lineup(name: "Guest", imageURL: "https://example.com/guest.jpg", showCount: 20),
            lineup(name: "Host", imageURL: "https://example.com/host.jpg", showCount: 10),
        ])

        let headliner = ShowRow.artworkComedian(for: show)
        let supporting = ShowRow.supportingLineup(for: show, excluding: headliner)

        #expect(supporting.map(\.name) == ["Feature", "Opener", "Guest", "Host"])
        #expect(ShowRow.supportingLabel(for: supporting) == "with Feature, Opener, Guest +1 more")
    }

    @Test("supporting lineup preserves performers at the three-avatar limit")
    func supportingLineupPreservesPerformersAtVisibleLimit() {
        let show = makeShow(lineup: [
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 40),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 30),
            lineup(name: "Opener", imageURL: "https://example.com/opener.jpg", showCount: 20),
            lineup(name: "Host", imageURL: "https://example.com/host.jpg", showCount: 10),
        ])

        let headliner = ShowRow.artworkComedian(for: show)
        let supporting = ShowRow.supportingLineup(for: show, excluding: headliner)

        #expect(supporting.map(\.name) == ["Feature", "Opener", "Host"])
        #expect(ShowRow.supportingLabel(for: supporting) == "with Feature, Opener, Host")
    }

    @Test("artwork comedian skips a more popular performer without absolute artwork")
    func artworkComedianSkipsFeaturedPerformerWithoutAbsoluteArtwork() {
        let show = makeShow(lineup: [
            lineup(name: "Headliner", imageURL: "/relative/headliner.jpg", showCount: 50, popularity: 100),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 10, popularity: 10),
        ])

        #expect(ShowRow.artworkComedian(for: show)?.name == "Feature")
        #expect(ShowRow.artworkImageURL(for: show) == "https://example.com/feature.jpg")
    }

    @Test("top lineup preserves order when show counts are absent")
    func topLineupPreservesOrderWhenCountsAbsent() {
        let show = makeShow(lineup: [
            lineup(name: "First", imageURL: "https://example.com/first.jpg", showCount: nil),
            lineup(name: "Second", imageURL: "https://example.com/second.jpg", showCount: nil),
        ])

        #expect(ShowRow.topLineup(for: show).map(\.name) == ["First", "Second"])
    }

    @Test("ShowRow.isOpenMic falls back to the show name when no tags are present")
    func showRowIsOpenMicMatchesName() {
        // Tags omitted on the fixture so this exercises the name-string
        // fallback path inside `ShowRow.isOpenMic`.
        let show = makeShow(name: "Tuesday Open Mic", lineup: nil)
        #expect(ShowRow.isOpenMic(show))
    }

    @Test("show row formats a single ticket price")
    func showRowFormatsSingleTicketPrice() {
        let show = makeShow(
            tickets: [.init(price: 24, purchaseUrl: "https://example.com/tickets", soldOut: false, _type: "General admission")],
            lineup: []
        )

        #expect(ShowRow.priceLabel(for: show) == "$24")
    }

    @Test("show row exposes the cheapest ticket price")
    func showRowExposesCheapestTicketPrice() {
        let show = makeShow(
            tickets: [
                .init(price: 35, purchaseUrl: "https://example.com/vip", soldOut: false, _type: "VIP"),
                .init(price: 20, purchaseUrl: "https://example.com/ga", soldOut: false, _type: "General admission"),
            ],
            lineup: []
        )

        #expect(ShowRow.priceLabel(for: show) == "$20")
    }

    @Test("show row formats free tickets")
    func showRowFormatsFreeTickets() {
        let show = makeShow(
            tickets: [.init(price: 0, purchaseUrl: "https://example.com/free", soldOut: false, _type: "RSVP")],
            lineup: []
        )

        #expect(ShowRow.priceLabel(for: show) == "Free")
    }

    @Test("show row omits price when no available ticket has a price")
    func showRowOmitsUnavailablePrice() {
        let show = makeShow(
            tickets: [
                .init(price: nil, purchaseUrl: "https://example.com/tickets", soldOut: false, _type: "General admission"),
                .init(price: 50, purchaseUrl: "https://example.com/sold-out", soldOut: true, _type: "VIP"),
            ],
            lineup: []
        )

        #expect(ShowRow.priceLabel(for: show) == nil)
    }

    @Test("previous price label exposes the price of every-ticket-sold-out shows for strikethrough")
    func previousPriceLabelExposesAllSoldOutPrice() {
        let show = makeShow(
            tickets: [
                .init(price: 20, purchaseUrl: "https://example.com/ga", soldOut: true, _type: "General admission"),
                .init(price: 35, purchaseUrl: "https://example.com/vip", soldOut: true, _type: "VIP"),
            ],
            lineup: []
        )

        #expect(ShowRow.priceLabel(for: show) == nil)
        #expect(ShowRow.previousPriceLabel(for: show) == "$20")
    }

    @Test("previous price label matches priceLabel when tickets are still available")
    func previousPriceLabelMatchesAvailableTickets() {
        let show = makeShow(
            tickets: [
                .init(price: 24, purchaseUrl: "https://example.com/tickets", soldOut: false, _type: "General admission"),
            ],
            lineup: []
        )

        #expect(ShowRow.previousPriceLabel(for: show) == ShowRow.priceLabel(for: show))
    }

    @Test("previous price label is nil when the show has no tickets at all")
    func previousPriceLabelNilWhenNoTickets() {
        let show = makeShow(tickets: [], lineup: [])

        #expect(ShowRow.previousPriceLabel(for: show) == nil)
    }

    @Test("show row exposes a trimmed room label")
    func showRowExposesTrimmedRoomLabel() {
        let show = makeShow(room: "  Village Underground  ", lineup: [])

        #expect(ShowRow.roomLabel(for: show) == "Village Underground")
    }

    @Test("show row omits blank room labels")
    func showRowOmitsBlankRoomLabels() {
        let show = makeShow(room: "   ", lineup: [])

        #expect(ShowRow.roomLabel(for: show) == nil)
    }

    @Test("show row omits room labels that duplicate the club name")
    func showRowOmitsRoomDuplicatingClubName() {
        let show = makeShow(
            clubName: "Punch Line Philly",
            room: "  punch line PHILLY ",
            lineup: []
        )

        #expect(ShowRow.roomLabel(for: show) == nil)
    }

    @Test("show row keeps room labels distinct from the club name")
    func showRowKeepsDistinctRoomLabels() {
        let show = makeShow(
            clubName: "Comedy Cellar",
            room: "Village Underground",
            lineup: []
        )

        #expect(ShowRow.roomLabel(for: show) == "Village Underground")
    }

    @Test("show row metadata keeps the date visible after artwork leads the row")
    func showRowMetadataKeepsDateVisible() {
        let show = makeShow(room: "Main Room", lineup: [])
        let metadata = ShowRow.metadata(for: show)

        #expect(metadata.first == ShowFormatting.listDate(show.date, timezoneID: show.timezone))
        #expect(metadata.contains("Main Room"))
    }

    private func makeShow(
        name: String = "Late show",
        clubName: String = "Comedy Cellar",
        clubCity: String? = nil,
        clubState: String? = nil,
        room: String? = nil,
        tickets: [Components.Schemas.Ticket] = [],
        tags: [Components.Schemas.Tag]? = nil,
        imageURL: String = "https://example.com/show.jpg",
        lineup: [Components.Schemas.ComedianLineup]?
    ) -> Components.Schemas.Show {
        Components.Schemas.Show(
            id: 1,
            clubId: 201,
            clubName: clubName,
            clubCity: clubCity,
            clubState: clubState,
            date: Date(timeIntervalSince1970: 1_710_000_000),
            tickets: tickets,
            name: name,
            lineup: lineup,
            tags: tags,
            room: room,
            imageUrl: imageURL,
            distanceMiles: 2.1
        )
    }

    private func lineup(
        name: String,
        imageURL: String,
        showCount: Int?,
        popularity: Double? = nil,
        parentComedian: Components.Schemas.ComedianLineup? = nil
    ) -> Components.Schemas.ComedianLineup {
        let id = name.utf8.reduce(0) { $0 + Int($1) }
        return Components.Schemas.ComedianLineup(
            name: name,
            imageUrl: imageURL,
            uuid: UUID().uuidString,
            id: id,
            socialData: popularity.map { .init(id: id, popularity: $0) },
            showCount: showCount,
            parentComedian: parentComedian
        )
    }

    private func showRowSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/Components/ShowRow.swift")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }
}

@Suite("Search agenda presentation", .serialized)
@MainActor
struct SearchAgendaPresentationTests {
    @Test("agenda suppresses a generated canonical performer subtitle without changing standalone rows")
    func canonicalIdentityIsNotRepeated() {
        let headliner = SearchAgendaFixtures.comedian("Taylor Tomlinson")
        let show = SearchAgendaFixtures.show()
        #expect(ShowRow.headlinerContext(for: show, headliner: headliner, context: .agenda) == nil)
        #expect(ShowRow.headlinerContext(for: show, headliner: headliner) == "Taylor Tomlinson")
        #expect(ShowRow(show: show).context == .standalone)
    }

    @Test("aliases and name-prefix collisions preserve canonical performer identity")
    func distinctIdentitiesRemainVisible() {
        let canonical = SearchAgendaFixtures.comedian("Canonical Visitor", id: 42)
        let alias = SearchAgendaFixtures.comedian("Visitor Alias", parent: canonical)
        let aliasShow = SearchAgendaFixtures.show("Visitor Alias", lineup: [alias])
        #expect(ShowRow.headlinerContext(for: aliasShow, headliner: canonical, context: .agenda) == canonical.name)

        let ann = SearchAgendaFixtures.comedian("Ann Lee")
        let prefixShow = SearchAgendaFixtures.show("Ann Leeman: Live", lineup: [ann])
        #expect(ShowRow.headlinerContext(for: prefixShow, headliner: ann, context: .agenda) == ann.name)
        let hyphenatedName = SearchAgendaFixtures.show("Ann Lee-Man: Live", lineup: [ann])
        #expect(ShowRow.headlinerContext(for: hyphenatedName, headliner: ann, context: .agenda) == ann.name)
    }

    @Test("named shows omit only a clearly repeated full performer prefix in the agenda")
    func namedShowPrefixesAvoidRepeatingIdentity() {
        let headliner = SearchAgendaFixtures.comedian("Taylor Tomlinson")
        for title in ["Taylor Tomlinson: Live", "Taylor Tomlinson & Friends", "Taylor Tomlinson — New Material", "Taylor Tomlinson - Live Special", "TAYLOR TOMLINSON:LIVE"] {
            let show = SearchAgendaFixtures.show(title)
            #expect(ShowRow.headlinerContext(for: show, headliner: headliner, context: .agenda) == nil)
            #expect(ShowRow.headlinerContext(for: show, headliner: headliner) == headliner.name)
        }
        let partial = SearchAgendaFixtures.show("Late Night with Taylor")
        #expect(ShowRow.headlinerContext(for: partial, headliner: headliner, context: .agenda) == headliner.name)
    }

    @Test("named ensemble shows retain headliner and supporting performers")
    func ensembleIdentityRemainsVisible() {
        let headliner = SearchAgendaFixtures.comedian("Sam Jay")
        let supporting = SearchAgendaFixtures.comedian("Ali Wong", id: 2)
        let show = SearchAgendaFixtures.show("Late Night Showcase", lineup: [headliner, supporting])
        #expect(ShowRow.primaryListTitle(for: show, headliner: headliner) == "Late Night Showcase")
        #expect(ShowRow.headlinerContext(for: show, headliner: headliner, context: .agenda) == "Sam Jay")
        #expect(ShowRow.supportingLineup(for: show, excluding: headliner).map(\.name) == ["Ali Wong"])
    }

    @Test("agenda times retain venue timezone and standalone metadata retains the full date")
    func timeAndDateStayVenueLocal() {
        var show = SearchAgendaFixtures.show()
        show.timezone = "America/Los_Angeles"
        #expect(ShowRow.timeLabel(for: show) == ShowFormatting.dateStack(show.date, timezoneID: show.timezone).time)
        #expect(ShowRow.timeLabel(for: show).contains("5:00"))
        #expect(ShowRow.metadata(for: show).first == ShowFormatting.listDate(show.date, timezoneID: show.timezone))
        show.timezone = "Invalid/Zone"
        #expect(ShowRow.timeLabel(for: show) == ShowFormatting.dateStack(show.date).time)
        show.timezone = nil
        #expect(ShowRow.timeLabel(for: show) == ShowFormatting.dateStack(show.date).time)
    }

    @Test("ticket states distinguish unknown price, free admission and sold-out prices")
    func ticketStatesRemainDistinct() {
        let unknown = SearchAgendaFixtures.show(price: nil)
        let free = SearchAgendaFixtures.show(price: 0)
        let soldOut = SearchAgendaFixtures.show(price: 35, soldOut: true)
        #expect(ShowRow.priceLabel(for: unknown) == nil)
        #expect(ShowRow.priceLabel(for: free) == "Free")
        #expect(ShowRow.priceLabel(for: soldOut) == nil)
        #expect(ShowRow.previousPriceLabel(for: soldOut) == "$35")
        #expect(soldOut.soldOut == true)
    }

    #if canImport(UIKit)
    @Test("long agenda titles grow beyond two lines within phone and tablet columns")
    func longTitlesRemainReadable() {
        let longTitle = "A wonderfully long comedy showcase with stories from every corner of the city"
        for width in [CGFloat(288), CGFloat(500)] {
            for size in [DynamicTypeSize.large, .accessibility5] {
                for lineup in [Optional<[Components.Schemas.ComedianLineup]>.none, [SearchAgendaFixtures.comedian("Taylor Tomlinson")]] {
                    let short = measure(SearchAgendaFixtures.show("Comedy Night", lineup: lineup), width: width, size: size)
                    let long = measure(SearchAgendaFixtures.show(longTitle, lineup: lineup), width: width, size: size)
                    let longer = measure(SearchAgendaFixtures.show(Array(repeating: longTitle, count: 3).joined(separator: " "), lineup: lineup), width: width, size: size)
                    #expect(long.height > short.height)
                    #expect(longer.height > long.height + 20, "Title must continue growing instead of truncating at two lines")
                    #expect(longer.width <= width + 1)
                    #expect(longer.height.isFinite)
                }
            }
        }
    }

    @Test("contextual performer names wrap at phone and tablet widths without clipping")
    func contextualNamesGrowAtAccessibilitySizes() {
        for width in [CGFloat(288), CGFloat(500)] {
            for size in [DynamicTypeSize.large, .accessibility5] {
                for context in [ShowRowContext.agenda, .standalone] {
                    func measured(_ name: String) -> CGSize {
                        let show = SearchAgendaFixtures.show("Comedy Night", lineup: [SearchAgendaFixtures.comedian(name)])
                        let controller = UIHostingController(rootView:
                            ShowRow(show: show, presentation: .compactTicket, context: context, performerContext: .followed(1))
                                .environment(\.appTheme, LaughTrackTheme())
                                .environment(\.dynamicTypeSize, size)
                                .environmentObject(TypedNavigationCoordinator<AppRoute>())
                        )
                        return controller.sizeThatFits(in: CGSize(width: width, height: 100_000))
                    }
                    let short = measured("Sam Jay")
                    let long = measured(Array(repeating: "A Performer With A Wonderfully Long Stage Name That Must Remain Readable", count: 3).joined(separator: " "))
                    #expect(long.height > short.height)
                    #expect(long.width <= width + 1)
                    #expect(long.height.isFinite)
                }
            }
        }
    }

    @Test("artwork-backed agenda rows preserve room information at accessibility sizes")
    func artworkRowsReserveSpaceForRoom() {
        for size in [DynamicTypeSize.large, .accessibility5] {
            let noRoom = measure(SearchAgendaFixtures.show(room: nil), width: 288, size: size)
            let withRoom = measure(SearchAgendaFixtures.show(room: "The Upstairs Listening Room"), width: 288, size: size)
            #expect(withRoom.height > noRoom.height, "A distinct room must render even when the row has performer artwork")
            #expect(withRoom.width <= 289)
        }
    }

    private func measure(_ show: Components.Schemas.Show, width: CGFloat, size: DynamicTypeSize) -> CGSize {
        let controller = UIHostingController(rootView:
            ShowRow(show: show, presentation: .compactTicket, context: .agenda)
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.dynamicTypeSize, size)
                .environmentObject(TypedNavigationCoordinator<AppRoute>())
        )
        return controller.sizeThatFits(in: CGSize(width: width, height: 100_000))
    }
    #endif
}
