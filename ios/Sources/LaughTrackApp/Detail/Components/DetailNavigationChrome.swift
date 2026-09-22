import SwiftUI
import LaughTrackBridge

enum DetailNavigationChrome {
    enum Entity {
        case club
        case comedian
        case podcast
        case show
    }

    static let extendsHeroBehindTopSafeArea = true

    /// Additional spacing below the status-bar safe-area inset for the
    /// sticky chrome bar. Hiding the system nav bar does NOT collapse the
    /// overlay's top inset — the chrome bar still receives the status-bar
    /// inset and renders at inset + this offset (see DetailStatusBarScrim,
    /// which relies on that inset to escape upward and cover the clock).
    /// Sits intentionally above the marquee hero's content padding so the
    /// back/favorite chrome reads as status-bar-adjacent rather than
    /// crowding the title row.
    static let stickyChromeTopOffset: CGFloat = 16

    /// Opacity/location stops for the top scrim that fades scrolled content
    /// out before it reaches the status bar clock. The scrim spans from the
    /// physical top of the screen to the bottom of the chrome bar: fully
    /// opaque behind the status bar, fading to clear past the chrome buttons
    /// so it reads as the same treatment as the marquee background's edge
    /// fade.
    static let statusBarScrimStops: [(opacity: Double, location: CGFloat)] = [
        (opacity: 1.0, location: 0),
        (opacity: 0.85, location: 0.55),
        (opacity: 0.0, location: 1)
    ]

    static func title(for entity: Entity) -> String {
        switch entity {
        case .club:
            return "Club"
        case .comedian:
            return "Comedian"
        case .podcast:
            return "Podcast"
        case .show:
            return "Show"
        }
    }
}

/// Describes the tab actually revealed by popping the shared stack.
struct DetailRootReturnPresentation {
    let tab: AppTab

    var title: String { tab.title }
    var accessibilityLabel: String { "Return to \(title)" }
    var systemImage: String {
        switch tab {
        case .nearMe: return "sparkles"
        case .search: return "magnifyingglass"
        case .favorites: return "heart.fill"
        }
    }
}

enum DetailScrolledIdentity {
    static let coordinateSpace = "detailViewport"
    static let chromeBottom = DetailNavigationChrome.stickyChromeTopOffset + 44

    static func resolve(title: String?, heroBottom: CGFloat?) -> String? {
        guard let heroBottom, heroBottom <= chromeBottom,
              let title = title?.trimmingCharacters(in: .whitespacesAndNewlines),
              !title.isEmpty else { return nil }
        return title
    }
}

struct DetailHeroBottomPreference: PreferenceKey {
    static let defaultValue: CGFloat? = nil

    static func reduce(value: inout CGFloat?, nextValue: () -> CGFloat?) {
        if let next = nextValue() { value = next }
    }
}

private struct DetailRootTabKey: EnvironmentKey {
    static let defaultValue = AppTab.nearMe
}

private struct DetailCompactIdentityKey: EnvironmentKey {
    static let defaultValue: String? = nil
}

extension EnvironmentValues {
    var detailRootTab: AppTab {
        get { self[DetailRootTabKey.self] }
        set { self[DetailRootTabKey.self] = newValue }
    }

    var detailCompactIdentity: String? {
        get { self[DetailCompactIdentityKey.self] }
        set { self[DetailCompactIdentityKey.self] = newValue }
    }
}

enum DetailCatalogComposition: Equatable {
    case compactStack
    case regularColumns

    static func resolve(horizontalSizeClass: UserInterfaceSizeClass?) -> Self {
        horizontalSizeClass == .regular ? .regularColumns : .compactStack
    }
}

/// Keeps the established phone detail stack while giving regular-width
/// catalog routes an intentional hero/content composition. The bounded
/// canvas prevents cards from stretching edge to edge on large iPads.
struct AdaptiveDetailCatalogLayout<Hero: View, Content: View>: View {
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    private let hero: Hero
    private let content: Content

    init(
        @ViewBuilder hero: () -> Hero,
        @ViewBuilder content: () -> Content
    ) {
        self.hero = hero()
        self.content = content()
    }

    @ViewBuilder
    var body: some View {
        if DetailCatalogComposition.resolve(horizontalSizeClass: horizontalSizeClass) == .regularColumns,
           !dynamicTypeSize.isAccessibilitySize {
            ViewThatFits(in: .horizontal) {
                HStack(alignment: .top, spacing: 32) {
                    hero.frame(width: 360)
                    content
                        .frame(minWidth: 340, maxWidth: .infinity, alignment: .leading)
                        .padding(.top, 96)
                }
                .padding(.horizontal, 32)
                // Give ViewThatFits the minimum usable two-column width as
                // its ideal width; long text must not reject a spacious canvas.
                .frame(minWidth: 796, idealWidth: 796, maxWidth: 1_120)

                stackedContent
            }
            .frame(maxWidth: .infinity, alignment: .center)
        } else {
            stackedContent
        }
    }

    private var stackedContent: some View {
        VStack(alignment: .leading, spacing: 0) {
            hero
            content
        }
    }
}

struct DetailFavoriteState {
    let isFavorite: Bool
    let isPending: Bool
    let action: () async -> Void
}

struct EntityDetailNavigationChrome: ViewModifier {
    @State private var heroBottom: CGFloat?

    let entity: DetailNavigationChrome.Entity
    let title: String?
    let favoriteState: DetailFavoriteState?

    init(
        entity: DetailNavigationChrome.Entity,
        title: String? = nil,
        favoriteState: DetailFavoriteState? = nil
    ) {
        self.entity = entity
        self.title = title
        self.favoriteState = favoriteState
    }

    func body(content: Content) -> some View {
        content
            .coordinateSpace(name: DetailScrolledIdentity.coordinateSpace)
            .onPreferenceChange(DetailHeroBottomPreference.self) { heroBottom = $0 }
            .environment(\.detailCompactIdentity, DetailScrolledIdentity.resolve(
                title: title,
                heroBottom: heroBottom
            ))
            #if os(iOS)
            .navigationTitle("")
            .navigationBarHidden(true)
            #else
            .navigationTitle(title ?? DetailNavigationChrome.title(for: entity))
            #endif
    }
}

struct DetailAtmosphereScrollContent: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(Color.clear)
            #if os(iOS)
            .scrollContentBackground(.hidden)
            #endif
    }
}

struct DetailAtmosphereRouteBackground: ViewModifier {
    func body(content: Content) -> some View {
        ZStack {
            LaughTrackAtmosphereBackground()
                .ignoresSafeArea()

            content
        }
    }
}

private struct DetailNavigationTitle: View {
    @Environment(\.appTheme) private var theme
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    let text: String

    var body: some View {
        if text.isEmpty {
            EmptyView()
        } else {
            Text(text)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                .lineLimit(2)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: dynamicTypeSize.isAccessibilitySize ? .infinity : 240, minHeight: 38)
                .padding(.horizontal, 8)
                .background(theme.laughTrackTokens.colors.surface, in: RoundedRectangle(cornerRadius: 12))
                .accessibilityAddTraits(.isHeader)
                .accessibilityIdentifier("detail.compactIdentity")
        }
    }
}

/// Sticky chrome bar overlaid at the top of every detail screen. Hosts the
/// back button (always present), the root-return button (when the stack is deep
/// enough for back and home to differ), and, when supplied, the favorite
/// toggle. Designed to be applied via `.overlay(alignment: .top)` on the
/// outer detail container so the back button remains tappable regardless of
/// scroll position or load phase.
struct DetailChromeBar: View {
    @Environment(\.detailRootTab) private var rootTab
    @Environment(\.detailCompactIdentity) private var compactIdentity
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    let onBack: () -> Void
    var onHome: (() -> Void)? = nil
    let favoriteState: DetailFavoriteState?

    var body: some View {
        VStack(spacing: 4) {
            ZStack {
                HStack(alignment: .center, spacing: 0) {
                    DetailBackButton(action: onBack)
                    if let onHome {
                        DetailHomeButton(rootTab: rootTab, action: onHome)
                    }
                    Spacer()
                    if let favoriteState {
                        DetailFavoriteToolbarButton(state: favoriteState)
                    }
                }
                if let compactIdentity, !dynamicTypeSize.isAccessibilitySize {
                    DetailNavigationTitle(text: compactIdentity)
                        .padding(.horizontal, onHome == nil ? 48 : 92)
                        .allowsHitTesting(false)
                }
            }
            if let compactIdentity, dynamicTypeSize.isAccessibilitySize {
                DetailNavigationTitle(text: compactIdentity)
                    .allowsHitTesting(false)
            }
        }
        .accessibilitySortPriority(1)
        .frame(minHeight: 44)
        .padding(.horizontal, 12)
        .padding(.top, DetailNavigationChrome.stickyChromeTopOffset)
        .background(alignment: .top) {
            DetailStatusBarScrim()
        }
    }
}

/// Top fade behind the sticky chrome so scrolled detail content dims out
/// before it reaches the status bar clock. It stays transparent over the
/// detail page's single atmosphere layer to avoid a visible seam between
/// the header controls and the hero content.
struct DetailStatusBarScrim: View {
    var body: some View {
        LinearGradient(
            stops: DetailNavigationChrome.statusBarScrimStops.map {
                .init(color: Color.black.opacity($0.opacity * 0.24), location: $0.location)
            },
            startPoint: .top,
            endPoint: .bottom
        )
        // The chrome bar overlay still receives the status-bar safe-area
        // inset, so the gradient fills the bar's bounds and then escapes
        // the inset to reach the physical top of the screen and cover the
        // clock.
        .ignoresSafeArea(.container, edges: .top)
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}

struct DetailBackButton: View {
    @Environment(\.appTheme) private var theme

    let action: () -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button(action: action) {
            ZStack {
                Circle()
                    .fill(laughTrack.colors.surface.opacity(0.94))
                    .overlay(
                        Circle()
                            .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                    )

                Image(systemName: "chevron.backward")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
            }
            .frame(width: 36, height: 36)
            .frame(width: 44, height: 44)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Back")
    }
}

/// Escape hatch for deep detail stacks. Its icon and spoken destination
/// identify the selected root tab that the shared stack will reveal.
struct DetailHomeButton: View {
    @Environment(\.appTheme) private var theme

    var rootTab: AppTab = .nearMe
    let action: () -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button(action: action) {
            ZStack {
                Circle()
                    .fill(laughTrack.colors.surface.opacity(0.94))
                    .overlay(
                        Circle()
                            .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                    )

                Image(systemName: DetailRootReturnPresentation(tab: rootTab).systemImage)
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
            }
            .frame(width: 36, height: 36)
            .frame(width: 44, height: 44)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(DetailRootReturnPresentation(tab: rootTab).accessibilityLabel)
        .accessibilityIdentifier("detail.returnToRoot")
    }
}

extension TypedNavigationCoordinator where Route == AppRoute {
    /// Pop-to-root action for the detail chrome's home button, or nil when
    /// the stack is shallow enough that back already returns to the root —
    /// a home button at depth one would duplicate the back button.
    var detailHomeAction: (() -> Void)? {
        guard routes.count > 1 else { return nil }
        return { [weak self] in self?.popToRoot() }
    }
}

struct DetailFavoriteToolbarButton: View {
    @Environment(\.appTheme) private var theme

    let state: DetailFavoriteState

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button {
            Task { await state.action() }
        } label: {
            ZStack {
                Circle()
                    .fill(laughTrack.colors.surface.opacity(0.94))
                    .overlay(
                        Circle()
                            .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                    )

                if state.isPending {
                    ProgressView()
                        .progressViewStyle(.circular)
                        .tint(laughTrack.colors.accent)
                } else {
                    Image(systemName: state.isFavorite ? "heart.fill" : "heart")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(state.isFavorite ? laughTrack.colors.accentStrong : laughTrack.colors.textPrimary)
                }
            }
            .frame(width: 36, height: 36)
            .frame(width: 44, height: 44)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(state.isPending)
        .accessibilityLabel(state.isFavorite ? "Remove favorite" : "Add favorite")
    }
}

#if canImport(UIKit)
import UIKit

/// Keeps UIKit's own interactive pop recognizer available with custom, hidden
/// navigation chrome. Install once in the persistent stack root so cancelled
/// transitions do not swap delegates while a gesture is in flight.
struct NativeInteractivePopSupport: UIViewControllerRepresentable {
    let playerChrome: NavigationPlayerChrome

    func makeUIViewController(context: Context) -> PopGestureHost {
        let controller = PopGestureHost()
        controller.playerChrome = playerChrome
        return controller
    }

    func updateUIViewController(_ controller: PopGestureHost, context: Context) {
        controller.installIfNeeded()
    }

    static func dismantleUIViewController(_ controller: PopGestureHost, coordinator: ()) {
        controller.restore()
    }

    final class PopGestureHost: UIViewController, UIGestureRecognizerDelegate {
        weak var playerChrome: NavigationPlayerChrome?
        private weak var attachedNavigationController: UINavigationController?
        private weak var originalDelegate: UIGestureRecognizerDelegate?
        private weak var recognizer: UIGestureRecognizer?
        private var originalEnabled = true

        override func loadView() {
            view = UIView()
            view.isUserInteractionEnabled = false
            view.backgroundColor = .clear
        }

        override func didMove(toParent parent: UIViewController?) {
            super.didMove(toParent: parent)
            if parent != nil { installIfNeeded() }
        }

        override func viewWillAppear(_ animated: Bool) {
            super.viewWillAppear(animated)
            coordinatePlayer()
        }

        override func viewWillDisappear(_ animated: Bool) {
            super.viewWillDisappear(animated)
            coordinatePlayer()
        }

        private func coordinatePlayer() {
            guard let navigation = navigationController,
                  let root = navigation.viewControllers.first,
                  let transition = navigation.transitionCoordinator
            else { return }
            playerChrome?.coordinate(transition, root: root)
        }

        override func viewDidAppear(_ animated: Bool) {
            super.viewDidAppear(animated)
            installIfNeeded()
            synchronizePlayerAfterAppearance()
        }

        override func viewDidDisappear(_ animated: Bool) {
            super.viewDidDisappear(animated)
            synchronizePlayerAfterAppearance()
        }

        private func synchronizePlayerAfterAppearance() {
            guard let navigation = navigationController ?? attachedNavigationController,
                  navigation.transitionCoordinator == nil,
                  let root = navigation.viewControllers.first
            else { return }
            playerChrome?.synchronize(rootVisible: navigation.topViewController === root)
        }

        func installIfNeeded() {
            guard let navigationController,
                  let gesture = navigationController.interactivePopGestureRecognizer
            else { return }
            if recognizer === gesture, gesture.delegate === self { return }
            restore()
            attachedNavigationController = navigationController
            recognizer = gesture
            originalDelegate = gesture.delegate
            originalEnabled = gesture.isEnabled
            gesture.delegate = self
            gesture.isEnabled = true
            synchronizePlayerAfterAppearance()
        }

        func restore() {
            // A later owner may have replaced us; never overwrite its policy.
            guard let recognizer, recognizer.delegate === self else { return }
            recognizer.delegate = originalDelegate
            recognizer.isEnabled = originalEnabled
            self.recognizer = nil
            attachedNavigationController = nil
            originalDelegate = nil
        }

        private var canBegin: Bool {
            guard let navigation = attachedNavigationController else { return false }
            return navigation.viewControllers.count > 1
                && navigation.transitionCoordinator == nil
                && navigation.presentedViewController == nil
                && navigation.topViewController?.presentedViewController == nil
                && navigation.viewIfLoaded?.window != nil
        }

        func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
            // The original delegate rejects a hidden navigation bar. Replace
            // only admission checks; UIKit still owns progress, completion,
            // cancellation, route synchronization and the transition animator.
            guard gestureRecognizer === recognizer, canBegin else { return false }
            if attachedNavigationController?.isNavigationBarHidden == true { return true }
            return originalDelegate?.gestureRecognizerShouldBegin?(gestureRecognizer) ?? true
        }

        func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
            originalDelegate?.gestureRecognizer?(gestureRecognizer, shouldReceive: touch) ?? true
        }

        func gestureRecognizer(
            _ gestureRecognizer: UIGestureRecognizer,
            shouldRecognizeSimultaneouslyWith otherGestureRecognizer: UIGestureRecognizer
        ) -> Bool {
            originalDelegate?.gestureRecognizer?(
                gestureRecognizer,
                shouldRecognizeSimultaneouslyWith: otherGestureRecognizer
            ) ?? false
        }

        func gestureRecognizer(
            _ gestureRecognizer: UIGestureRecognizer,
            shouldRequireFailureOf otherGestureRecognizer: UIGestureRecognizer
        ) -> Bool {
            originalDelegate?.gestureRecognizer?(
                gestureRecognizer,
                shouldRequireFailureOf: otherGestureRecognizer
            ) ?? false
        }

        func gestureRecognizer(
            _ gestureRecognizer: UIGestureRecognizer,
            shouldBeRequiredToFailBy otherGestureRecognizer: UIGestureRecognizer
        ) -> Bool {
            originalDelegate?.gestureRecognizer?(
                gestureRecognizer,
                shouldBeRequiredToFailBy: otherGestureRecognizer
            ) ?? false
        }
    }
}
#endif

#if canImport(UIKit)
/// A persistent mini-player can share UIKit's interactive navigation timeline
/// without taking ownership of the navigation animator or route binding.
@MainActor
final class NavigationPlayerChrome: ObservableObject {
    private weak var playerView: UIView?
    private var rootIsVisible = true
    private var activeTransition: UIViewControllerTransitionCoordinator?

    func attach(_ view: UIView) {
        playerView = view
        guard activeTransition == nil else { return }
        view.transform = transform(rootVisible: rootIsVisible)
    }

    /// Nonanimated navigation has no transition coordinator. Only completed
    /// appearance callbacks (or first attachment) synchronize this fallback.
    func synchronize(rootVisible: Bool) {
        guard activeTransition == nil else { return }
        rootIsVisible = rootVisible
        UIView.performWithoutAnimation {
            playerView?.transform = transform(rootVisible: rootVisible)
        }
    }

    func coordinate(_ transition: UIViewControllerTransitionCoordinator, root: UIViewController) {
        guard activeTransition == nil,
              let from = transition.viewController(forKey: .from),
              let to = transition.viewController(forKey: .to),
              (from === root || to === root),
              from.navigationController === to.navigationController,
              from.navigationController != nil
        else { return }
        let returningToRoot = to === root
        activeTransition = transition
        let registered = transition.animate(alongsideTransition: { [weak self] _ in
            guard let self else { return }
            if UIAccessibility.isReduceMotionEnabled {
                UIView.performWithoutAnimation {
                    self.playerView?.transform = self.transform(rootVisible: returningToRoot)
                }
            } else {
                self.playerView?.transform = self.transform(rootVisible: returningToRoot)
            }
        }, completion: { [weak self] context in
            guard let self else { return }
            self.rootIsVisible = context.isCancelled ? !returningToRoot : returningToRoot
            self.activeTransition = nil
            self.playerView?.transform = self.transform(rootVisible: self.rootIsVisible)
        })
        if !registered {
            activeTransition = nil
            rootIsVisible = returningToRoot
            playerView?.transform = transform(rootVisible: rootIsVisible)
        }
    }

    private func transform(rootVisible: Bool) -> CGAffineTransform {
        CGAffineTransform(translationX: 0, y: rootVisible ? 0 : PodcastMiniPlayerLayout.rootTabBarClearance)
    }
}

struct NavigationPlayerContainer<Player: View>: UIViewControllerRepresentable {
    @Environment(\.self) private var environment
    @EnvironmentObject private var navigationCoordinator: TypedNavigationCoordinator<AppRoute>
    let chrome: NavigationPlayerChrome
    let isVisible: Bool
    let player: Player

    func makeUIViewController(context: Context) -> PlayerHost {
        PlayerHost(content: hostedContent, chrome: chrome)
    }

    func updateUIViewController(_ controller: PlayerHost, context: Context) {
        controller.host.rootView = hostedContent
        controller.isPlayerVisible = isVisible
        controller.view.setNeedsLayout()
        chrome.attach(controller.host.view)
    }

    private var hostedContent: AnyView {
        // Forward app dependencies, not a snapshot of every environment value.
        // Size classes, Dynamic Type, Reduce Motion and modal dismissal belong
        // to the hosting controller's current native traits/presentation.
        AnyView(player
            .environment(\.appTheme, environment.appTheme)
            .environment(\.serviceContainer, environment.serviceContainer)
            .environment(\.openURL, environment.openURL)
            .environmentObject(navigationCoordinator))
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiViewController: PlayerHost, context: Context) -> CGSize? {
        guard isVisible else { return CGSize(width: proposal.width ?? 0, height: 0) }
        let width = proposal.width ?? uiViewController.view.bounds.width
        let playerSize = uiViewController.host.sizeThatFits(in: CGSize(width: width, height: .greatestFiniteMagnitude))
        return CGSize(width: width, height: playerSize.height + PodcastMiniPlayerLayout.rootTabBarClearance)
    }

    final class PlayerHost: UIViewController {
        let host: UIHostingController<AnyView>
        var isPlayerVisible = true
        private let chrome: NavigationPlayerChrome

        init(content: AnyView, chrome: NavigationPlayerChrome) {
            host = UIHostingController(rootView: content)
            self.chrome = chrome
            super.init(nibName: nil, bundle: nil)
        }

        required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

        override func loadView() {
            view = PlayerPassthroughView()
            view.backgroundColor = .clear
            addChild(host)
            host.view.backgroundColor = .clear
            host.view.clipsToBounds = false
            view.addSubview(host.view)
            host.didMove(toParent: self)
            chrome.attach(host.view)
        }

        override func viewDidLayoutSubviews() {
            super.viewDidLayoutSubviews()
            let size = host.sizeThatFits(in: CGSize(width: view.bounds.width, height: .greatestFiniteMagnitude))
            // Bounds/center preserve an in-flight transform; setting frame on
            // a transformed view would perturb UIKit's interactive animation.
            host.view.bounds = CGRect(origin: .zero, size: CGSize(width: view.bounds.width, height: isPlayerVisible ? size.height : 0))
            host.view.center = CGPoint(x: view.bounds.midX, y: host.view.bounds.height / 2)
        }
    }
}

private final class PlayerPassthroughView: UIView {
    override func hitTest(_ point: CGPoint, with event: UIEvent?) -> UIView? {
        let hit = super.hitTest(point, with: event)
        return hit === self ? nil : hit
    }
}
#endif
