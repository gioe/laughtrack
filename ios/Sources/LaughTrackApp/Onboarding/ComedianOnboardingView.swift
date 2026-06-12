import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ComedianOnboardingView: View {
    let apiClient: Client
    let favorites: ComedianFavoriteStore

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var authManager: AuthManager
    @StateObject private var model: ComedianOnboardingModel

    /// How the comedian list is presented: suggestions deal into the swipe
    /// deck (engaging, broad signal); an explicit search renders a tappable
    /// results list (precise, "I know who I want").
    private enum BrowseMode {
        case deck
        case searchResults
    }

    @State private var mode: BrowseMode = .deck

    /// Position of the top card in `model.comedians`. Purely presentational —
    /// favorite state lives in the model/store; passing a card just advances.
    @State private var deckIndex = 0
    @State private var dragOffset: CGSize = .zero

    private static let swipeThreshold: CGFloat = 100
    private static let flingDistance: CGFloat = 560

    /// Remaining undealt cards at which the deck prefetches another
    /// suggestions batch, so swiping normally never hits the bottom.
    private static let deckPrefetchThreshold = 4

    @MainActor
    init(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        model: ComedianOnboardingModel? = nil
    ) {
        self.apiClient = apiClient
        self.favorites = favorites
        _model = StateObject(
            wrappedValue: model ?? ComedianOnboardingModel()
        )
    }

    var body: some View {
        let tokens = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: theme.spacing.xl) {
                marqueeHeader

                VStack(alignment: .leading, spacing: theme.spacing.xl) {
                    LaughTrackSearchField(placeholder: "Search comedians", text: $model.searchText) {
                        Button {
                            Task { await runSearch() }
                        } label: {
                            Image(systemName: "magnifyingglass")
                                .font(.system(size: theme.iconSizes.md, weight: .semibold))
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Search comedians")
                        .accessibilityIdentifier(LaughTrackViewTestID.onboardingSearchButton)
                    }
                    .modifier(SearchFieldInputBehavior())
                    .onSubmit {
                        Task { await runSearch() }
                    }
                    .accessibilityIdentifier(LaughTrackViewTestID.onboardingSearchField)

                    comedianSection
                }
                .padding(.horizontal, theme.spacing.lg)
            }
            .padding(.bottom, theme.spacing.xxl)
        }
        .background(tokens.colors.canvas.ignoresSafeArea())
        .safeAreaInset(edge: .bottom) {
            continueBar
        }
        .overlay(alignment: .topTrailing) {
            skipButton
        }
        .task {
            guard model.comedians.isEmpty else { return }
            await model.loadInitialComedians(apiClient: apiClient, favorites: favorites)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.onboardingScreen)
    }

    private func runSearch() async {
        let query = model.searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        await model.search(model.searchText, apiClient: apiClient, favorites: favorites)
        mode = query.isEmpty ? .deck : .searchResults
        deckIndex = 0
        dragOffset = .zero
    }

    private func returnToDeck() async {
        model.searchText = ""
        mode = .deck
        deckIndex = 0
        dragOffset = .zero
        await model.loadInitialComedians(apiClient: apiClient, favorites: favorites)
    }

    private var marqueeHeader: some View {
        let tokens = theme.laughTrackTokens

        return VStack(spacing: 10) {
            // Clearance so the centered eyebrow/title clear the floating
            // skip chip pinned to the top-trailing corner.
            Color.clear.frame(height: 32)

            Text("Welcome to LaughTrack")
                .font(.system(size: 11, weight: .semibold, design: .rounded))
                .tracking(2.2)
                .textCase(.uppercase)
                .foregroundStyle(tokens.colors.accentStrong)

            Text("Pick comedians to follow")
                .font(.system(size: 26, weight: .heavy, design: .rounded))
                .tracking(0.4)
                .textCase(.uppercase)
                .multilineTextAlignment(.center)
                .foregroundStyle(.white)
                .fixedSize(horizontal: false, vertical: true)
                .shadow(color: .black.opacity(0.6), radius: 4, x: 0, y: 2)
                .padding(.horizontal, theme.spacing.xl)

            Text("Swipe right to follow, left to pass — or search for anyone. Aim for 3 so LaughTrack can surface better show alerts.")
                .font(tokens.typography.body)
                .foregroundStyle(tokens.colors.textSecondary)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.horizontal, theme.spacing.xl)

            bulbCounter
                .padding(.top, theme.spacing.xs)
        }
        .padding(.bottom, theme.spacing.lg)
        .frame(maxWidth: .infinity)
        .background(marqueeStageBackground)
    }

    /// Total favorites across both browse modes, from the store rather than
    /// the model's current list — searching must not appear to reset picks.
    private var selectedCount: Int {
        favorites.favoritedCount
    }

    /// Three marquee bulbs that light up as the user favorites comedians,
    /// echoing the dashed bulb-ring poster frames used across detail heroes.
    private var bulbCounter: some View {
        let tokens = theme.laughTrackTokens
        let litCount = min(selectedCount, model.suggestedFavoriteTarget)

        return HStack(spacing: theme.spacing.sm) {
            ForEach(0..<model.suggestedFavoriteTarget, id: \.self) { index in
                let isLit = index < litCount

                Circle()
                    .fill(isLit ? tokens.colors.accentStrong : tokens.colors.surfaceElevated)
                    .overlay(
                        Circle().stroke(
                            isLit ? tokens.colors.accentStrong : tokens.colors.borderSubtle,
                            lineWidth: 1
                        )
                    )
                    .frame(width: 10, height: 10)
                    .shadow(color: tokens.colors.accentStrong.opacity(isLit ? 0.7 : 0), radius: 5)
                    .scaleEffect(isLit ? 1.0 : 0.85)
            }

            Text("\(selectedCount)/\(model.suggestedFavoriteTarget) selected")
                .font(tokens.typography.metadata)
                .foregroundStyle(tokens.colors.accentStrong)
                .accessibilityIdentifier(LaughTrackViewTestID.onboardingFavoriteCount)
                .padding(.leading, theme.spacing.xs)
        }
        .animation(.spring(duration: 0.35), value: selectedCount)
    }

    private var marqueeStageBackground: some View {
        let tokens = theme.laughTrackTokens

        return ZStack {
            tokens.colors.heroStart

            RadialGradient(
                colors: [
                    tokens.colors.accent.opacity(0.2),
                    tokens.colors.accent.opacity(0.0)
                ],
                center: UnitPoint(x: 0.5, y: 0.25),
                startRadius: 20,
                endRadius: 260
            )
        }
        .mask(
            LinearGradient(
                stops: [
                    .init(color: .black, location: 0),
                    .init(color: .black, location: 0.72),
                    .init(color: .black.opacity(0.4), location: 0.92),
                    .init(color: .black.opacity(0), location: 1)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        )
        .ignoresSafeArea(edges: .top)
    }

    @ViewBuilder
    private var comedianSection: some View {
        switch model.phase {
        case .idle, .loading:
            ProgressView("Loading comedians")
                .tint(theme.laughTrackTokens.colors.accent)
                .frame(maxWidth: .infinity, alignment: .center)
        case .failure(let message):
            InlineStatusMessage(message: message)
        case .loaded, .saving:
            switch mode {
            case .deck:
                VStack(spacing: theme.spacing.lg) {
                    deck
                    deckControls
                }
            case .searchResults:
                searchResults
            }
        }
    }

    private var searchResults: some View {
        let tokens = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: theme.spacing.md) {
            HStack {
                Text("Results")
                    .font(.system(size: 11, weight: .semibold, design: .rounded))
                    .tracking(2.2)
                    .textCase(.uppercase)
                    .foregroundStyle(tokens.colors.accentStrong)

                Spacer()

                Button {
                    Task { await returnToDeck() }
                } label: {
                    HStack(spacing: theme.spacing.xs) {
                        Image(systemName: "rectangle.portrait.on.rectangle.portrait.angled")
                            .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                        Text("Back to the deck")
                    }
                    .font(tokens.typography.metadata)
                    .foregroundStyle(tokens.colors.textSecondary)
                    .padding(.horizontal, theme.spacing.md)
                    .padding(.vertical, theme.spacing.sm)
                    .background(Capsule().fill(tokens.colors.surfaceElevated))
                    .overlay(Capsule().stroke(tokens.colors.borderSubtle, lineWidth: 1))
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Back to suggested comedians")
            }

            if model.comedians.isEmpty {
                Text("No comedians matched that search. Try another name, or head back to the deck.")
                    .font(tokens.typography.body)
                    .foregroundStyle(tokens.colors.textSecondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding(.vertical, theme.spacing.xl)
            } else {
                LazyVStack(spacing: theme.spacing.md) {
                    ForEach(model.comedians, id: \.uuid) { comedian in
                        ComedianOnboardingRow(
                            comedian: comedian,
                            isFavorite: favorites.value(for: comedian.uuid, fallback: comedian.isFavorite),
                            isPending: favorites.isPending(comedian.uuid)
                        ) {
                            await model.toggleFavorite(
                                uuid: comedian.uuid,
                                apiClient: apiClient,
                                favorites: favorites,
                                authManager: authManager
                            )
                        }
                    }
                }
            }
        }
    }

    private var visibleDeck: [Components.Schemas.ComedianSearchItem] {
        Array(model.comedians.dropFirst(deckIndex).prefix(3))
    }

    private var topComedian: Components.Schemas.ComedianSearchItem? {
        visibleDeck.first
    }

    private var deck: some View {
        ZStack {
            if visibleDeck.isEmpty {
                if model.suggestionsExhausted {
                    deckExhaustedCard
                } else {
                    deckRefillCard
                }
            } else {
                // Reversed so the top card (depth 0) draws last, on top.
                ForEach(Array(visibleDeck.enumerated()).reversed(), id: \.element.uuid) { depth, comedian in
                    let isTop = depth == 0

                    ComedianSwipeCard(
                        comedian: comedian,
                        isFavorite: favorites.value(for: comedian.uuid, fallback: comedian.isFavorite),
                        dragAmount: isTop ? dragOffset.width : 0
                    )
                    .scaleEffect(isTop ? 1 : 1 - CGFloat(depth) * 0.05)
                    .offset(
                        x: isTop ? dragOffset.width : 0,
                        y: isTop ? dragOffset.height * 0.35 : CGFloat(depth) * 14
                    )
                    .rotationEffect(.degrees(isTop ? dragOffset.width / 14 : 0))
                    .gesture(dragGesture(for: comedian), including: isTop ? .all : .none)
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel(comedian.name)
                    .accessibilityIdentifier(LaughTrackViewTestID.onboardingComedianRow(comedian.id))
                }
            }
        }
        .animation(.spring(duration: 0.3), value: deckIndex)
        .padding(.bottom, theme.spacing.md)
    }

    private func dragGesture(for comedian: Components.Schemas.ComedianSearchItem) -> some Gesture {
        DragGesture(minimumDistance: 12)
            .onChanged { value in
                dragOffset = value.translation
            }
            .onEnded { value in
                if value.translation.width > Self.swipeThreshold {
                    swipeAway(comedian, towards: 1, follow: true)
                } else if value.translation.width < -Self.swipeThreshold {
                    swipeAway(comedian, towards: -1, follow: false)
                } else {
                    withAnimation(.spring(duration: 0.3)) {
                        dragOffset = .zero
                    }
                }
            }
    }

    /// Fling the top card off-screen, optionally favoriting it, then advance
    /// the deck once the fling animation has played out.
    private func swipeAway(
        _ comedian: Components.Schemas.ComedianSearchItem,
        towards direction: CGFloat,
        follow: Bool
    ) {
        withAnimation(.easeOut(duration: 0.22)) {
            dragOffset = CGSize(width: direction * Self.flingDistance, height: dragOffset.height * 0.35)
        }

        if follow {
            let alreadyFavorite = favorites.value(for: comedian.uuid, fallback: comedian.isFavorite)
            if !alreadyFavorite {
                Task {
                    await model.toggleFavorite(
                        uuid: comedian.uuid,
                        apiClient: apiClient,
                        favorites: favorites,
                        authManager: authManager
                    )
                }
            }
        }

        Task {
            try? await Task.sleep(nanoseconds: 220_000_000)
            var transaction = Transaction()
            transaction.disablesAnimations = true
            withTransaction(transaction) {
                dragOffset = .zero
            }
            deckIndex += 1
            await prefetchMoreComediansIfNeeded()
        }
    }

    /// Keep the deck endless: once the undealt remainder dips below the
    /// threshold, draw another suggestions batch in the background.
    private func prefetchMoreComediansIfNeeded() async {
        guard mode == .deck else { return }
        guard model.comedians.count - deckIndex <= Self.deckPrefetchThreshold else { return }
        await model.loadMoreSuggestions(apiClient: apiClient, favorites: favorites)
    }

    private var deckControls: some View {
        let tokens = theme.laughTrackTokens
        let isPending = topComedian.map { favorites.isPending($0.uuid) } ?? false

        return HStack(spacing: theme.spacing.xl) {
            // Pass
            Button {
                guard let topComedian else { return }
                swipeAway(topComedian, towards: -1, follow: false)
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 22, weight: .bold))
                    .foregroundStyle(tokens.colors.textSecondary)
                    .frame(width: 58, height: 58)
                    .background(Circle().fill(tokens.colors.surfaceElevated))
                    .overlay(Circle().stroke(tokens.colors.borderSubtle, lineWidth: 1))
            }
            .buttonStyle(.plain)
            .disabled(topComedian == nil)
            .accessibilityLabel("Pass")

            // Rewind
            Button {
                withAnimation(.spring(duration: 0.3)) {
                    deckIndex = max(0, deckIndex - 1)
                    dragOffset = .zero
                }
            } label: {
                Image(systemName: "arrow.uturn.backward")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(tokens.colors.textSecondary)
                    .frame(width: 42, height: 42)
                    .background(Circle().fill(tokens.colors.surfaceElevated))
                    .overlay(Circle().stroke(tokens.colors.borderSubtle, lineWidth: 1))
            }
            .buttonStyle(.plain)
            .disabled(deckIndex == 0)
            .opacity(deckIndex == 0 ? 0.4 : 1)
            .accessibilityLabel("Bring back previous comedian")

            // Follow
            Button {
                guard let topComedian else { return }
                swipeAway(topComedian, towards: 1, follow: true)
            } label: {
                Group {
                    if isPending {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Image(systemName: "heart.fill")
                            .font(.system(size: 24, weight: .bold))
                            .foregroundStyle(.white)
                    }
                }
                .frame(width: 64, height: 64)
                .background(Circle().fill(tokens.colors.accentStrong))
                .shadow(color: tokens.colors.accentStrong.opacity(0.55), radius: 10, x: 0, y: 2)
            }
            .buttonStyle(.plain)
            .disabled(topComedian == nil || isPending)
            .accessibilityLabel("Follow")
            .accessibilityIdentifier(
                topComedian.map { LaughTrackViewTestID.onboardingComedianFavoriteButton($0.id) }
                    ?? ""
            )
        }
        .frame(maxWidth: .infinity)
    }

    /// Shown when swiping outpaced the background prefetch: the deck is
    /// momentarily empty but the suggestion pool isn't exhausted yet. The
    /// `.task` covers the edge where no prefetch is in flight (e.g. the
    /// last one failed) so the empty state always resolves — either fresh
    /// cards arrive or the model flips to exhausted.
    private var deckRefillCard: some View {
        ProgressView("Finding more comedians")
            .tint(theme.laughTrackTokens.colors.accent)
            .frame(maxWidth: .infinity)
            .padding(.vertical, theme.spacing.xxl)
            .task {
                await model.loadMoreSuggestions(apiClient: apiClient, favorites: favorites)
            }
    }

    private var deckExhaustedCard: some View {
        let tokens = theme.laughTrackTokens

        return VStack(spacing: theme.spacing.md) {
            ZStack {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(tokens.colors.surfaceMuted)
                    .frame(width: 120, height: 120)
                    .overlay {
                        Image(systemName: "music.mic")
                            .font(.system(size: 44, weight: .semibold))
                            .foregroundStyle(tokens.colors.accentStrong)
                    }

                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .strokeBorder(
                        tokens.colors.accentStrong,
                        style: StrokeStyle(
                            lineWidth: 2.5,
                            lineCap: .round,
                            lineJoin: .round,
                            dash: [0.5, 7]
                        )
                    )
                    .frame(width: 130, height: 130)
                    .shadow(color: tokens.colors.accentStrong.opacity(0.65), radius: 5)
                    .shadow(color: tokens.colors.accentStrong.opacity(0.3), radius: 11)
            }
            .padding(.top, theme.spacing.sm)

            Text("That's the lineup")
                .font(.system(size: 20, weight: .heavy, design: .rounded))
                .tracking(0.4)
                .textCase(.uppercase)
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.6), radius: 4, x: 0, y: 2)

            Text("Search for more comedians, or continue with your picks.")
                .font(tokens.typography.body)
                .foregroundStyle(tokens.colors.textSecondary)
                .multilineTextAlignment(.center)

            if !model.comedians.isEmpty {
                // A fresh weighted-random deal (not a replay of the same
                // cards) — it also clears the exhausted flag, so a deck
                // ended by a transient fetch failure recovers here.
                Button {
                    Task { await returnToDeck() }
                } label: {
                    HStack(spacing: theme.spacing.xs) {
                        Image(systemName: "arrow.counterclockwise")
                            .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                        Text("Deal them again")
                    }
                    .font(tokens.typography.metadata)
                    .foregroundStyle(tokens.colors.accentStrong)
                    .padding(.horizontal, theme.spacing.md)
                    .padding(.vertical, theme.spacing.sm)
                    .background(Capsule().fill(tokens.colors.surfaceElevated))
                    .overlay(Capsule().stroke(tokens.colors.borderSubtle, lineWidth: 1))
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.vertical, theme.spacing.xl)
        .padding(.horizontal, theme.spacing.lg)
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(tokens.colors.surface)
                .overlay(
                    RoundedRectangle(cornerRadius: 20, style: .continuous)
                        .stroke(tokens.colors.borderSubtle, lineWidth: 1)
                )
        )
    }

    private var continueBar: some View {
        let tokens = theme.laughTrackTokens

        return LaughTrackButton(model.phase == .saving ? "Saving..." : "Continue", systemImage: "checkmark") {
            Task {
                await model.complete(apiClient: apiClient, authManager: authManager)
            }
        }
        .disabled(!model.canContinue)
        .shadow(
            color: tokens.colors.accentStrong.opacity(model.canContinue ? 0.45 : 0),
            radius: 12,
            x: 0,
            y: 2
        )
        .accessibilityIdentifier(LaughTrackViewTestID.onboardingContinueButton)
        .padding(.horizontal, theme.spacing.lg)
        .padding(.top, theme.spacing.md)
        .padding(.bottom, theme.spacing.sm)
        .background(
            tokens.colors.canvas
                .overlay(alignment: .top) {
                    Rectangle()
                        .fill(tokens.colors.borderSubtle)
                        .frame(height: 1)
                }
                .ignoresSafeArea(edges: .bottom)
        )
    }

    private var skipButton: some View {
        let tokens = theme.laughTrackTokens

        return Button {
            Task {
                await model.skip(apiClient: apiClient, authManager: authManager)
            }
        } label: {
            HStack(spacing: theme.spacing.xs) {
                Text("Skip")
                Image(systemName: "arrow.right")
                    .font(.system(size: theme.iconSizes.sm, weight: .semibold))
            }
            .font(tokens.typography.metadata)
            .foregroundStyle(tokens.colors.textSecondary)
            .padding(.horizontal, theme.spacing.md)
            .padding(.vertical, theme.spacing.sm)
            .background(Capsule().fill(tokens.colors.surfaceElevated))
            .overlay(Capsule().stroke(tokens.colors.borderSubtle, lineWidth: 1))
            .shadowStyle(tokens.shadows.card)
        }
        .buttonStyle(.plain)
        .disabled(!model.canContinue)
        .padding(.top, theme.spacing.sm)
        .padding(.trailing, theme.spacing.lg)
        .accessibilityIdentifier(LaughTrackViewTestID.onboardingSkipButton)
    }
}

/// One search result row: a mini marquee poster that gains the dashed
/// bulb-ring glow once favorited. The whole row is tappable so picking an
/// exact comedian from search is a single hit anywhere on the card.
private struct ComedianOnboardingRow: View {
    @Environment(\.appTheme) private var theme

    let comedian: Components.Schemas.ComedianSearchItem
    let isFavorite: Bool
    let isPending: Bool
    let toggleFavorite: () async -> Void

    private static let posterSize: CGFloat = 56
    private static let posterFrameInset: CGFloat = 8

    var body: some View {
        LaughTrackCard(tone: isFavorite ? .accent : .standard, density: .compact) {
            HStack(spacing: theme.spacing.md) {
                artwork

                VStack(alignment: .leading, spacing: theme.spacing.xs) {
                    Text(comedian.name)
                        .font(theme.laughTrackTokens.typography.cardTitle)
                        .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                }

                Spacer(minLength: 0)

                FavoriteButton(isFavorite: isFavorite, isPending: isPending, action: toggleFavorite)
                    .accessibilityIdentifier(LaughTrackViewTestID.onboardingComedianFavoriteButton(comedian.id))
            }
        }
        .contentShape(Rectangle())
        .onTapGesture {
            guard !isPending else { return }
            Task { await toggleFavorite() }
        }
        .accessibilityIdentifier(LaughTrackViewTestID.onboardingComedianRow(comedian.id))
    }

    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            RemoteImageView(
                urlString: comedian.imageUrl,
                aspectRatio: 1
            )
            .frame(width: Self.posterSize, height: Self.posterSize)
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(Color.black.opacity(0.55), lineWidth: 1)
            )

            if isFavorite {
                RoundedRectangle(cornerRadius: 11, style: .continuous)
                    .strokeBorder(
                        laughTrack.colors.accentStrong,
                        style: StrokeStyle(
                            lineWidth: 2,
                            lineCap: .round,
                            lineJoin: .round,
                            dash: [0.5, 6]
                        )
                    )
                    .frame(
                        width: Self.posterSize + Self.posterFrameInset,
                        height: Self.posterSize + Self.posterFrameInset
                    )
                    .shadow(color: laughTrack.colors.accentStrong.opacity(0.65), radius: 4)
                    .shadow(color: laughTrack.colors.accentStrong.opacity(0.3), radius: 9)
                    .transition(.scale(scale: 0.8).combined(with: .opacity))
            }
        }
        .frame(
            width: Self.posterSize + Self.posterFrameInset,
            height: Self.posterSize + Self.posterFrameInset
        )
        .animation(.spring(duration: 0.3), value: isFavorite)
    }
}

/// One card in the onboarding swipe deck: the comedian's photo as a marquee
/// poster wrapped in the dashed bulb-ring frame used across detail heroes,
/// with FOLLOW / PASS stamps that fade in as the card is dragged.
private struct ComedianSwipeCard: View {
    @Environment(\.appTheme) private var theme

    let comedian: Components.Schemas.ComedianSearchItem
    let isFavorite: Bool
    /// Horizontal drag translation of the card; drives the stamp opacity.
    let dragAmount: CGFloat

    // Matches MarqueeHero.posterSize so onboarding cards read as the same
    // poster artifact used on detail heroes — and leaves the deck controls
    // clear of the continue bar on smaller screens.
    private static let posterSize: CGFloat = 196
    private static let frameInset: CGFloat = 10

    var body: some View {
        let tokens = theme.laughTrackTokens

        VStack(spacing: theme.spacing.md) {
            ZStack {
                RemoteImageView(
                    urlString: comedian.imageUrl,
                    aspectRatio: 1
                )
                .frame(width: Self.posterSize, height: Self.posterSize)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(Color.black.opacity(0.55), lineWidth: 1)
                )

                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .strokeBorder(
                        tokens.colors.accentStrong,
                        style: StrokeStyle(
                            lineWidth: 2.5,
                            lineCap: .round,
                            lineJoin: .round,
                            dash: [0.5, 7]
                        )
                    )
                    .frame(
                        width: Self.posterSize + Self.frameInset,
                        height: Self.posterSize + Self.frameInset
                    )
                    .shadow(color: tokens.colors.accentStrong.opacity(0.65), radius: 5)
                    .shadow(color: tokens.colors.accentStrong.opacity(0.3), radius: 11)
            }
            .frame(
                width: Self.posterSize + Self.frameInset,
                height: Self.posterSize + Self.frameInset
            )

            Text(comedian.name)
                .font(.system(size: 20, weight: .heavy, design: .rounded))
                .tracking(0.4)
                .textCase(.uppercase)
                .multilineTextAlignment(.center)
                .foregroundStyle(.white)
                .lineLimit(2)
                .minimumScaleFactor(0.7)
                .shadow(color: .black.opacity(0.6), radius: 4, x: 0, y: 2)
                .padding(.horizontal, theme.spacing.lg)

            if isFavorite {
                HStack(spacing: theme.spacing.xs) {
                    Image(systemName: "heart.fill")
                        .font(.system(size: 11, weight: .bold))
                    Text("Following")
                        .font(.system(size: 11, weight: .semibold, design: .rounded))
                        .tracking(2.2)
                        .textCase(.uppercase)
                }
                .foregroundStyle(tokens.colors.accentStrong)
            }
        }
        .padding(.vertical, theme.spacing.lg)
        .frame(maxWidth: .infinity)
        .background(cardBackground)
        .overlay(alignment: .topLeading) {
            swipeStamp("Follow", color: tokens.colors.accentStrong)
                .rotationEffect(.degrees(-12))
                .opacity(dragAmount > 0 ? min(1, dragAmount / 110) : 0)
                .padding(theme.spacing.lg)
        }
        .overlay(alignment: .topTrailing) {
            swipeStamp("Pass", color: tokens.colors.textSecondary)
                .rotationEffect(.degrees(12))
                .opacity(dragAmount < 0 ? min(1, -dragAmount / 110) : 0)
                .padding(theme.spacing.lg)
        }
    }

    private var cardBackground: some View {
        let tokens = theme.laughTrackTokens

        return RoundedRectangle(cornerRadius: 20, style: .continuous)
            .fill(tokens.colors.surface)
            .overlay(
                ZStack {
                    tokens.colors.heroStart

                    RadialGradient(
                        colors: [
                            tokens.colors.accent.opacity(0.2),
                            tokens.colors.accent.opacity(0.0)
                        ],
                        center: UnitPoint(x: 0.5, y: 0.4),
                        startRadius: 16,
                        endRadius: 220
                    )
                }
                .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(tokens.colors.borderSubtle, lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.35), radius: 10, x: 0, y: 6)
    }

    private func swipeStamp(_ label: String, color: Color) -> some View {
        Text(label)
            .font(.system(size: 18, weight: .heavy, design: .rounded))
            .tracking(2.2)
            .textCase(.uppercase)
            .foregroundStyle(color)
            .padding(.horizontal, 14)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .strokeBorder(
                        color,
                        style: StrokeStyle(
                            lineWidth: 2.5,
                            lineCap: .round,
                            lineJoin: .round,
                            dash: [0.5, 7]
                        )
                    )
                    .shadow(color: color.opacity(0.5), radius: 5)
            )
    }
}
