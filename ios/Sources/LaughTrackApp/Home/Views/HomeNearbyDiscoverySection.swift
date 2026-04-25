import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct HomeNearbyDiscoverySection: View {
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @StateObject private var model: HomeNearbyDiscoveryModel

    init(
        apiClient: Client,
        nearbyPreferenceStore: NearbyPreferenceStore,
        nearbyLocationController: NearbyLocationController
    ) {
        self.apiClient = apiClient
        _model = StateObject(
            wrappedValue: HomeNearbyDiscoveryModel(
                nearbyPreferenceStore: nearbyPreferenceStore,
                nearbyLocationController: nearbyLocationController
            )
        )
    }

    var body: some View {
        DiscoveryCard(title: "Nearby tonight") {
            VStack(alignment: .leading, spacing: theme.spacing.lg) {
                if model.shouldShowPrompt {
                    promptContent
                } else if let preference = model.activeNearbyPreference {
                    nearbyResultsContent(preference: preference)
                } else {
                    collapsedContent
                }
            }
        }
        .task(id: model.requestKey) {
            await model.refresh(apiClient: apiClient)
        }
    }

    @ViewBuilder
    private var promptContent: some View {
        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            LaughTrackSectionHeader(
                eyebrow: "Nearby",
                title: "Start with the room around you",
                subtitle: "Use your current location or drop in a ZIP code. LaughTrack keeps the rest of home available even if you skip this for now."
            )

            HStack(spacing: theme.spacing.sm) {
                LaughTrackBadge("Optional", systemImage: "hand.raised", tone: .neutral)
                LaughTrackBadge("No lock-in", systemImage: "location.slash", tone: .highlight)
            }

            VStack(spacing: theme.spacing.sm) {
                LaughTrackButton(
                    model.isResolvingLocation ? "Finding your ZIP…" : "Use current location",
                    systemImage: "location.fill"
                ) {
                    Task {
                        await model.useCurrentLocation()
                    }
                }
                .disabled(model.isResolvingLocation)

                LaughTrackButton("Enter a ZIP instead", systemImage: "mappin.and.ellipse", tone: .secondary) {
                    model.presentZipEntry()
                }

                LaughTrackButton("Not now", systemImage: "arrow.right", tone: .tertiary) {
                    model.dismissPrompt()
                }
            }

            if model.isEditingZip {
                homeZipField
            }

            statusMessages
        }
    }

    @ViewBuilder
    private func nearbyResultsContent(preference: NearbyPreference) -> some View {
        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            LaughTrackSectionHeader(
                eyebrow: "Nearby",
                title: "Shows around ZIP \(preference.zipCode)",
                subtitle: preference.source == .manual
                    ? "Using your saved ZIP and radius preference from home."
                    : "Using the ZIP closest to your current location."
            )

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: theme.spacing.sm) {
                    LaughTrackBadge("ZIP \(preference.zipCode)", systemImage: "mappin.and.ellipse", tone: .neutral)
                    LaughTrackBadge("Within \(preference.distanceMiles) mi", systemImage: "location.fill", tone: .highlight)
                    LaughTrackBadge(
                        preference.source == .manual ? "Saved manually" : "Current location",
                        systemImage: preference.source == .manual ? "slider.horizontal.3" : "location.north.line",
                        tone: .accent
                    )
                }
            }

            HStack(spacing: theme.spacing.sm) {
                LaughTrackButton("Change ZIP", systemImage: "pencil", tone: .secondary, fullWidth: false) {
                    model.presentZipEntry()
                }
                LaughTrackButton("Clear nearby", systemImage: "location.slash", tone: .tertiary, fullWidth: false) {
                    model.clearNearby()
                }
            }

            if model.isEditingZip {
                homeZipField
            }

            statusMessages

            switch model.phase {
            case .idle, .loading:
                LoadingCard()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.refresh(apiClient: apiClient) },
                    signIn: { coordinator.push(.settings) }
                )
            case .success(let result):
                if result.items.isEmpty {
                    EmptyCard(message: "No nearby shows matched this ZIP yet. Broaden the radius below or clear nearby filters.")
                } else {
                    VStack(alignment: .leading, spacing: theme.spacing.md) {
                        SearchResultsSummary(count: result.items.count, total: result.total)

                        if result.zipCapTriggered {
                            InlineStatusMessage(message: "That ZIP was broadened by the server because it covered too many locations. Tighten the ZIP or clear nearby filters.")
                        }

                        ForEach(Array(result.items.prefix(3)), id: \.id) { show in
                            Button {
                                coordinator.open(.show(show.id))
                            } label: {
                                ShowRow(show: show)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var collapsedContent: some View {
        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            LaughTrackSectionHeader(
                eyebrow: "Nearby",
                title: "Nearby browsing is paused",
                subtitle: "You can keep browsing nationally below, or turn nearby back on whenever you want."
            )

            VStack(spacing: theme.spacing.sm) {
                LaughTrackButton(
                    model.isResolvingLocation ? "Finding your ZIP…" : "Use current location",
                    systemImage: "location.fill"
                ) {
                    Task {
                        await model.useCurrentLocation()
                    }
                }
                .disabled(model.isResolvingLocation)

                LaughTrackButton("Enter a ZIP instead", systemImage: "mappin.and.ellipse", tone: .secondary) {
                    model.presentZipEntry()
                }
            }

            if model.isEditingZip {
                homeZipField
            }

            statusMessages
        }
    }

    private var homeZipField: some View {
        LaughTrackLabeledField(title: "ZIP", detail: "5 digits") {
            VStack(alignment: .leading, spacing: theme.spacing.sm) {
                TextField("10012", text: $model.zipCodeDraft)
                    .modifier(SearchFieldInputBehavior())
                    #if os(iOS)
                    .keyboardType(UIKeyboardType.numberPad)
                    #endif

                LaughTrackButton("Use this ZIP", systemImage: "checkmark", tone: .secondary, fullWidth: false) {
                    _ = model.applyManualZip()
                }
            }
        }
    }

    @ViewBuilder
    private var statusMessages: some View {
        if let zipValidationMessage = model.zipValidationMessage {
            InlineStatusMessage(message: zipValidationMessage)
        }

        if let locationMessage = model.locationMessage {
            InlineStatusMessage(message: locationMessage)
        }
    }
}
