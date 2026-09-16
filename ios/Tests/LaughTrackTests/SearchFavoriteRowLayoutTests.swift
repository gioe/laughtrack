import Foundation
import Testing
import SwiftUI
import LaughTrackBridge
@testable import LaughTrackApp

#if canImport(UIKit)
import UIKit

@Suite("Search loading visual capture", .serialized)
@MainActor
struct SearchLoadingVisualCaptureTests {
    @Test("capture loading results at standard and accessibility sizes")
    func captureLoading() async throws {
        for size in [DynamicTypeSize.large, .accessibility5] {
            for kind in 0..<4 {
                let host = HostedView(
                    ScrollView {
                        VStack(alignment: .leading, spacing: 16) {
                            Text(["Shows", "Comedians", "Clubs", "Podcasts"][kind])
                                .font(LaughTrackTheme().laughTrackTokens.typography.screenTitle)
                            Group {
                                switch kind {
                                case 0: ShowsListSkeleton(context: .agenda)
                                case 1: ComediansListSkeleton()
                                case 2: ClubsListSkeleton()
                                default: PodcastsListSkeleton()
                                }
                            }
                        }.padding(16)
                    }
                    .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
                    .environment(\.appTheme, LaughTrackTheme())
                    .environment(\.dynamicTypeSize, size)
                    .preferredColorScheme(.dark), freshWindow: true
                )
                await host.settle()
                let data = try #require(try host.snapshot().pngData())
                let suffix = size.isAccessibilitySize ? "AX5" : "standard"
                let path = FileManager.default.temporaryDirectory.appendingPathComponent("task4008-\(kind)-\(suffix).png")
                try data.write(to: path)
                print("Search loading capture: \(path.path)")
                #if compiler(>=6.2)
                Attachment.record(Array(data), named: path.lastPathComponent)
                #endif
            }
        }
    }
}

@Suite("Search loading geometry", .serialized)
@MainActor
struct SearchLoadingGeometryTests {
    @Test("capture components and full Search loading states")
    func captureScreens() async throws {
        try await SearchLoadingVisualCaptureTests().captureLoading()
        try await SearchQueryVisualCaptureTests().captureCategories()
    }

    @Test("redacted entity rows retain loaded dimensions at narrow and accessibility widths")
    func entityGeometry() async throws {
        for kind in [LaughTrackSearchEntityKind.comedian, .club, .podcast] {
            for size in [DynamicTypeSize.large, .accessibility5] {
                for width in [CGFloat(288), 370] {
                    try await compareRedaction(LoadingEntityGeometryRow(kind: kind), width: width, size: size)
                }
            }
        }
    }

    @Test("ticket redaction preserves agenda and independent date-stub geometry")
    func ticketGeometry() async throws {
        #expect(ShowsListSkeleton().context == .standalone)
        for context in [ShowRowContext.agenda, .standalone] {
            for size in [DynamicTypeSize.large, .accessibility5] {
                for width in [CGFloat(288), 370] {
                    let row = ShowRow(show: ShowsListSkeleton.placeholder, presentation: .compactTicket, context: context)
                    try await compareRedaction(row, width: width, size: size)
                }
            }
        }
    }

    @Test("loading results use the loaded two-column composition in regular width")
    func regularComposition() {
        let skeleton = EntityRowsSkeleton(kind: .club, label: "Loading clubs")
        let single = measure(skeleton.environment(\.horizontalSizeClass, .compact), width: 768, size: .large)
        let grid = measure(skeleton.environment(\.horizontalSizeClass, .regular), width: 768, size: .large)
        #expect(grid.height < single.height - 100)
        #expect(abs(grid.width - 768) < 1)
        let accessible = measure(skeleton.environment(\.horizontalSizeClass, .regular), width: 768, size: .accessibility5)
        #expect(abs(accessible.width - 768) < 1)
        #expect(accessible.height > grid.height)
    }

    @Test("Reduce Motion stays static and stops a running shimmer")
    func reduceMotionStopsShimmer() async throws {
        let preference = LoadingMotionPreference()
        let host = HostedView(LoadingMotionProbe(preference: preference)
            .environment(\.appTheme, LaughTrackTheme()), freshWindow: true)
        await host.settle()
        let first = try host.snapshot().pngData()
        try await Task.sleep(for: .milliseconds(300))
        #expect(try host.snapshot().pngData() == first)
        preference.reduceMotion = false
        await host.settle()
        try await Task.sleep(for: .milliseconds(300))
        _ = try host.snapshot()
        preference.reduceMotion = true
        await host.settle()
        let stopped = try host.snapshot().pngData()
        #expect(stopped == first)
        try await Task.sleep(for: .milliseconds(300))
        #expect(try host.snapshot().pngData() == stopped)
    }

    private func measure<V: View>(_ view: V, width: CGFloat, size: DynamicTypeSize) -> CGSize {
        let controller = UIHostingController(rootView: view
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.dynamicTypeSize, size))
        return controller.sizeThatFits(in: CGSize(width: width, height: .greatestFiniteMagnitude))
    }

    private func compareRedaction<V: View>(_ row: V, width: CGFloat, size: DynamicTypeSize) async throws {
        let geometry = SearchRowGeometryRecorder()
        let host = HostedView(
            ScrollView {
                VStack {
                    row.background(SearchRowGeometryProbe { geometry.row = $0 })
                    row.redacted(reason: .placeholder)
                        .background(SearchRowGeometryProbe { geometry.favorite = $0 })
                }.frame(width: width)
            }
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.dynamicTypeSize, size), freshWindow: true
        )
        await host.settle(iterations: 3)
        let loaded = try #require(geometry.row)
        let placeholder = try #require(geometry.favorite)
        #expect(abs(loaded.height - placeholder.height) < 1, "\(size), width \(width): loaded \(loaded), placeholder \(placeholder)")
        #expect(abs(placeholder.width - width) < 1)
    }
}

private struct LoadingEntityGeometryRow: View {
    let kind: LaughTrackSearchEntityKind
    var body: some View { EntityRowsSkeleton(kind: kind, label: "Loading").row }
}

@MainActor
private final class LoadingMotionPreference: ObservableObject {
    @Published var reduceMotion = true
}

private struct LoadingMotionProbe: View {
    @ObservedObject var preference: LoadingMotionPreference
    var body: some View {
        Rectangle().fill(Color.gray).frame(width: 200, height: 80)
            .modifier(SkeletonShimmerModifier(reduceMotion: preference.reduceMotion))
    }
}

@Suite("Search entity row visual capture", .serialized)
@MainActor
struct SearchEntityRowVisualCaptureTests {
    @Test("capture shared Search and Library rows at standard and accessibility sizes")
    func captureRows() async throws {
        for size in [DynamicTypeSize.large, .accessibility5] {
            for index in 0..<3 {
                let title = ["Taylor Tomlinson", "The Comedy Store", "Good One: A Podcast About Jokes"][index]
                let subtitle = ["", "West Hollywood, CA", "Vulture"][index]
                let kind: LaughTrackSearchEntityKind = [.comedian, .club, .podcast][index]
                let artwork = ["taylor", "comedy-store", "history-hyenas"][index]
                let host = HostedView(
                    ScrollView {
                        VStack(spacing: 16) {
                            LaughTrackSearchEntityRow(title: title, subtitle: subtitle, imageURL: "http://127.0.0.1:8765/artwork/\(artwork).png", kind: kind, action: {}) {
                                FavoriteButton(isFavorite: false, isPending: false) {}
                            }
                            LaughTrackSearchEntityRow(title: "A wonderfully long name with more to say", subtitle: subtitle, imageURL: nil, kind: kind, action: {}) {
                                FavoriteButton(isFavorite: true, isPending: false) {}
                            }
                            LaughTrackSearchEntityRow(title: "Saving favorite", imageURL: nil, kind: kind, action: {}) {
                                FavoriteButton(isFavorite: true, isPending: true) {}
                            }
                        }
                        .padding(16)
                    }
                    .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
                    .environment(\.appTheme, LaughTrackTheme())
                    .environment(\.dynamicTypeSize, size)
                    .preferredColorScheme(.dark), freshWindow: true
                )
                await host.settle()
                let data = try #require(try host.snapshot().pngData())
                let textSize = size.isAccessibilitySize ? "AX5" : "standard"
                let name = ["comedian", "club", "podcast"][index]
                let path = FileManager.default.temporaryDirectory.appendingPathComponent("task4004-\(name)-\(textSize).png")
                try data.write(to: path)
                print("Search row capture: \(path.path)")
                #if compiler(>=6.2)
                Attachment.record(Array(data), named: path.lastPathComponent)
                #endif

                // The longest AX rows scroll past the viewport. Capture the
                // pending accessory separately so its rendered size is visible.
                if size.isAccessibilitySize {
                    let pendingHost = HostedView(
                        VStack {
                            LaughTrackSearchEntityRow(title: title, subtitle: subtitle, imageURL: nil, kind: kind, action: {}) {
                                FavoriteButton(isFavorite: true, isPending: true) {}
                            }
                            Spacer()
                        }
                        .padding(16)
                        .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
                        .environment(\.appTheme, LaughTrackTheme())
                        .environment(\.dynamicTypeSize, size)
                        .preferredColorScheme(.dark), freshWindow: true
                    )
                    await pendingHost.settle()
                    let pendingData = try #require(try pendingHost.snapshot().pngData())
                    let pendingPath = FileManager.default.temporaryDirectory.appendingPathComponent("task4004-\(name)-AX5-pending.png")
                    try pendingData.write(to: pendingPath)
                    print("Search row capture: \(pendingPath.path)")
                    #if compiler(>=6.2)
                    Attachment.record(Array(pendingData), named: pendingPath.lastPathComponent)
                    #endif
                }
            }
        }
    }
}
#endif

@Suite("Search favorite row layout", .serialized)
struct SearchFavoriteRowLayoutTests {
    #if canImport(UIKit)
    @Test("long entity names continue growing beyond the former two-line limit")
    @MainActor
    func longTitlesExpandAtStandardAndAccessibilitySizes() {
        let longTitle = "A wonderfully long comedy name with stories from every corner of the city"
        let longerTitle = Array(repeating: longTitle, count: 3).joined(separator: " ")
        for kind in [LaughTrackSearchEntityKind.comedian, .club, .podcast] {
            for size in [DynamicTypeSize.large, .accessibility5] {
                let shortHeight = measuredRowHeight(title: "Comedy", kind: kind, size: size)
                let longHeight = measuredRowHeight(title: longTitle, kind: kind, size: size)
                let longerHeight = measuredRowHeight(title: longerTitle, kind: kind, size: size)

                #expect(longHeight > shortHeight + 20)
                // Both long titles already exceed two lines at this width.
                // A capped label would stop adding height for the longer name.
                #expect(longerHeight > longHeight + 60)
                #expect(longerHeight.isFinite)
            }
        }
    }

    @Test("rendered favorite states preserve independent 44-point targets and row bounds")
    @MainActor
    func renderedFavoriteTargetsStayWithinRows() async throws {
        for kind in [LaughTrackSearchEntityKind.comedian, .club, .podcast] {
            for size in [DynamicTypeSize.large, .accessibility5] {
                var stateSizes: [CGSize] = []
                for state in [(saved: false, pending: false), (saved: true, pending: false), (saved: true, pending: true)] {
                    let geometry = SearchRowGeometryRecorder()
                    let host = HostedView(
                        ScrollView {
                            LaughTrackSearchEntityRow(
                                title: "A wonderfully long name with more to say",
                                subtitle: "Long author and location metadata remains readable",
                                imageURL: nil,
                                kind: kind,
                                action: {},
                                accessibilityIdentifier: "layout.detail"
                            ) {
                                FavoriteButton(isFavorite: state.saved, isPending: state.pending) {}
                                    .background(SearchRowGeometryProbe { geometry.favorite = $0 })
                            }
                            .background(SearchRowGeometryProbe { geometry.row = $0 })
                            .frame(width: 288)
                        }
                        .environment(\.appTheme, LaughTrackTheme())
                        .environment(\.dynamicTypeSize, size),
                        freshWindow: true
                    )
                    await host.settle()
                    let detail = try host.requireView(withIdentifier: "layout.detail")
                    let detailFrame = detail.convert(detail.bounds, to: nil)
                    let favorite = try #require(geometry.favorite)
                    let row = try #require(geometry.row)

                    #expect(favorite.width >= 44)
                    #expect(favorite.height >= 44)
                    #expect(detailFrame.width >= 44)
                    #expect(detailFrame.height >= 44)
                    #expect(!detailFrame.intersects(favorite))
                    #expect(row.insetBy(dx: -1, dy: -1).contains(detailFrame))
                    #expect(row.insetBy(dx: -1, dy: -1).contains(favorite))
                    #expect(abs(row.width - 288) < 1)
                    stateSizes.append(row.size)
                }
                let initial = try #require(stateSizes.first)
                for size in stateSizes.dropFirst() {
                    #expect(abs(size.width - initial.width) < 1)
                    #expect(abs(size.height - initial.height) < 1)
                }
            }
        }
    }

    @Test("rows without a favorite keep their complete detail target inside a narrow column")
    @MainActor
    func rowsWithoutFavoriteStayWithinProposedWidth() async throws {
        let cases: [(LaughTrackSearchEntityKind, String, String)] = [
            (.comedian, "Taylor Tomlinson", "A wonderfully long touring comedian description"),
            (.club, "Hollywood Improv", "Hollywood, CA"),
            (.podcast, "Good One: A Podcast About Jokes", "Chris Distefano & Yannis Pappas"),
        ]
        for (kind, title, subtitle) in cases {
            for size in [DynamicTypeSize.large, .accessibility5] {
                let geometry = SearchRowGeometryRecorder()
                let host = HostedView(
                    ScrollView {
                        AdaptiveSearchResults(spacing: 16) {
                            LaughTrackSearchEntityRow(
                                title: title,
                                subtitle: subtitle,
                                imageURL: nil,
                                kind: kind,
                                action: {},
                                accessibilityIdentifier: "layout.detail-without-favorite"
                            )
                            .background(SearchRowGeometryProbe { geometry.row = $0 })
                        }
                        .frame(width: 288)
                    }
                    .environment(\.appTheme, LaughTrackTheme())
                    .environment(\.dynamicTypeSize, size)
                    .environment(\.horizontalSizeClass, .compact),
                    freshWindow: true
                )
                await host.settle()
                let detail = try host.requireView(withIdentifier: "layout.detail-without-favorite")
                let detailFrame = detail.convert(detail.bounds, to: nil)
                let row = try #require(geometry.row)
                #expect(abs(row.width - 288) < 1, "Row exceeds the proposed column: \(row)")
                #expect(detailFrame.width >= 44)
                #expect(detailFrame.height >= 44)
                #expect(row.insetBy(dx: -1, dy: -1).contains(detailFrame),
                        "Detail target must remain inside the complete row: detail=\(detailFrame), row=\(row)")
                #expect(detail.accessibilityLabel == "\(title), \(subtitle)")
            }
        }
    }

    @Test("club filter chips do not widen the result column at accessibility sizes")
    @MainActor
    func clubFilterChipsRespectTheResultColumnWidth() async throws {
        let scenarios: [(width: CGFloat, location: String, active: Bool, size: DynamicTypeSize)] = [
            (288, "Location New York, NY", true, .large),
            (288, "Location New York, NY", true, .accessibility5),
            (343, "Location", false, .large),
            (343, "Location", false, .accessibility5),
        ]
        for scenario in scenarios {
            let geometry = SearchRowGeometryRecorder()
            let column = SearchRowGeometryRecorder()
            let host = HostedView(
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        ChipFlowLayout(spacing: 8, rowSpacing: 8) {
                            if !scenario.active {
                                PillDropdownTrigger(
                                    id: "layout.club-distance",
                                    selected: ShowDistanceOption.city,
                                    triggerLabel: { $0.title },
                                    openDropdownID: .constant(nil)
                                )
                            }
                            PillDropdownTrigger(
                                id: "layout.club-sort",
                                selected: ClubSortOption.mostActive,
                                triggerLabel: { $0.title },
                                openDropdownID: .constant(nil)
                            )
                            PillSheetTrigger(
                                title: scenario.location,
                                systemImage: "mappin.and.ellipse",
                                isActive: scenario.active,
                                action: {}
                            )
                            if !scenario.active {
                                PillSheetTrigger(
                                    title: "Filters", systemImage: "line.3.horizontal.decrease", action: {}
                                )
                            }
                        }
                        AdaptiveSearchResults(spacing: 16) {
                            LaughTrackSearchEntityRow(
                                title: "Hollywood Improv", subtitle: "Hollywood, CA",
                                imageURL: nil, kind: .club, action: {},
                                accessibilityIdentifier: "layout.club-detail"
                            )
                            .background(SearchRowGeometryProbe { geometry.row = $0 })
                        }
                    }
                    .background(SearchRowGeometryProbe { column.row = $0 })
                    .frame(width: scenario.width)
                }
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.dynamicTypeSize, scenario.size)
                .environment(\.horizontalSizeClass, .compact),
                freshWindow: true
            )
            await host.settle()
            let row = try #require(geometry.row)
            let content = try #require(column.row)
            let detail = try host.requireView(withIdentifier: "layout.club-detail")
            let detailFrame = detail.convert(detail.bounds, to: nil)
            #expect(content.width <= scenario.width + 1, "Filter ancestor must respect the \(scenario.width)pt proposal: \(content)")
            #expect(row.width <= scenario.width + 1, "Oversized filters must not widen sibling results: \(row)")
            #expect(detailFrame.width <= scenario.width + 1, "Detail must stay inside the visible column: \(detailFrame)")
        }
    }

    @MainActor
    private func measuredRowHeight(title: String, kind: LaughTrackSearchEntityKind, size: DynamicTypeSize) -> CGFloat {
        let controller = UIHostingController(rootView:
            LaughTrackSearchEntityRow(title: title, imageURL: nil, kind: kind, action: {}) {
                FavoriteButton(isFavorite: false, isPending: false) {}
            }
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.dynamicTypeSize, size)
        )
        return controller.sizeThatFits(in: CGSize(width: 288, height: 100_000)).height
    }
    #endif

    @Test("shared entity rows use dense vertical padding without reducing readable text")
    func sharedEntityRowsUseDenseVerticalMetrics() {
        let metrics = LaughTrackSearchEntityRowMetrics.standard

        #expect(metrics.verticalCardPadding == 12)
        #expect(metrics.titleLineLimit == nil)
        #expect(metrics.subtitleLineLimit == 2)
    }

    @Test("entity search result rows use the shared adaptive composition")
    func entitySearchRowsUseSharedAdaptiveComposition() throws {
        for fileName in [
            "ComediansDiscoveryView.swift",
            "ClubsDiscoveryView.swift",
            "PodcastSearchView.swift",
        ] {
            let source = try String(contentsOf: searchViewSourceURL(named: fileName), encoding: .utf8)
            #expect(source.contains("AdaptiveSearchResults(spacing: theme.spacing.md)"))
        }
    }

    @Test("comedian search favorite button is integrated into the entity row")
    func comedianSearchFavoriteButtonIsIntegratedIntoEntityRow() throws {
        let source = try String(contentsOf: searchViewSourceURL(named: "ComediansDiscoveryView.swift"), encoding: .utf8)
        let block = source[source.range(of: "struct ComedianRow: View")!.lowerBound...]

        #expect(block.contains("LaughTrackSearchEntityRow("))
        #expect(block.contains("action: openDetail"))
        #expect(block.contains("FavoriteButton("))
    }

    @Test("entity artwork preserves distinct silhouettes without decorative frames")
    func entityArtworkUsesDistinctShapes() {
        #expect(LaughTrackSearchEntityKind.comedian.artworkShape == .circle)
        #expect(LaughTrackSearchEntityKind.club.artworkShape == .roundedRectangle(cornerRadius: 12))
        #expect(LaughTrackSearchEntityKind.podcast.artworkShape == .roundedRectangle(cornerRadius: 6))
    }

    @Test("shared entity rows announce distinguishing subtitle metadata")
    func sharedEntityRowsIncludeSubtitleInAccessibilityLabel() throws {
        let source = try String(contentsOf: browseComponentsSourceURL(), encoding: .utf8)
        let block = try sourceBlock(in: source, from: "struct LaughTrackSearchEntityRow", to: "struct LaughTrackEntityRowDesign")

        #expect(block.contains(".accessibilityLabel(rowAccessibilityLabel)"))
        #expect(block.contains("return \"\\(title), \\(subtitle)\""))
    }

    @Test("club wall headshot frame supports visible and hidden nameplate variants")
    func clubWallHeadshotFrameSupportsVisibleAndHiddenNameplateVariants() throws {
        let source = try String(contentsOf: componentSourceURL(named: "ClubWallHeadshotFrame.swift"), encoding: .utf8)

        #expect(source.contains("enum ClubWallHeadshotCaptionVisibility"))
        #expect(source.contains("case visible"))
        #expect(source.contains("case hidden"))
        #expect(source.contains("var captionVisibility: ClubWallHeadshotCaptionVisibility = .visible"))
        #expect(source.contains("var rotationDegrees: Double = 0"))
        #expect(source.contains("private var framedContent: some View"))
        #expect(source.contains("private var matInset: CGFloat"))
        #expect(source.contains("private var captionBottomMatInset: CGFloat"))
        #expect(source.contains("frameWidth > 110 ? 8 : 6"))
        #expect(source.contains(".padding(.top, matInset)"))
        #expect(source.contains(".padding(.horizontal, matInset)"))
        #expect(source.contains(".padding(.bottom, captionBottomMatInset)"))
        #expect(source.contains("if captionVisibility == .visible"))
        #expect(source.contains("captionText"))
        #expect(!source.contains("ZStack(alignment: .bottom)"))
        #expect(!source.contains("captionPlateBottomInset"))
        #expect(!source.contains("matBottomInset"))
    }

    @Test("podcast search favorite button is integrated into the entity row")
    func podcastSearchFavoriteButtonIsIntegratedIntoEntityRow() throws {
        let source = try String(contentsOf: searchViewSourceURL(named: "PodcastSearchView.swift"), encoding: .utf8)
        let block = try sourceBlock(in: source, from: "struct PodcastSearchRow: View", to: "private func toggle")

        #expect(block.contains("private func openPodcastDetail()"))
        #expect(block.contains("openPodcastDetail()"))
        #expect(block.contains("FavoriteButton("))
    }

    private func searchViewSourceURL(named fileName: String, filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/Search/Views/\(fileName)")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }

    private func componentSourceURL(named fileName: String, filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/Components/\(fileName)")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }

    private func browseComponentsSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        return iosRoot.appendingPathComponent(
            "Sources/LaughTrackApp/DesignSystem/LaughTrackBrowseComponents.swift"
        )
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

#if canImport(UIKit)
@MainActor
private final class SearchRowGeometryRecorder {
    var row: CGRect?
    var favorite: CGRect?
}

/// A test-only background reads actual layout without adding identifiers or
/// accessibility nodes to the production control hierarchy.
private struct SearchRowGeometryProbe: UIViewRepresentable {
    let record: (CGRect) -> Void

    func makeUIView(context: Context) -> ProbeView {
        let view = ProbeView()
        view.isUserInteractionEnabled = false
        view.record = record
        return view
    }

    func updateUIView(_ view: ProbeView, context: Context) {
        view.record = record
        view.setNeedsLayout()
    }

    final class ProbeView: UIView {
        var record: ((CGRect) -> Void)?

        override func layoutSubviews() {
            super.layoutSubviews()
            guard window != nil, !bounds.isEmpty else { return }
            record?(convert(bounds, to: nil))
        }
    }
}
#endif
