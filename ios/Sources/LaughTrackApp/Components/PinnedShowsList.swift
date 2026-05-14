import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

/// Reusable shows list scoped to a specific entity — pass the club name to
/// lock the list to one venue's shows, or the comedian name to lock it to one
/// performer's appearances. Owns the `@StateObject<ShowsListModel>` so the
/// parent detail screen doesn't have to thread the model's lifecycle through
/// its own view-model.
///
/// The pinned name pre-fills the corresponding filter, hides the matching
/// search field in the toolbar, and is locked in for the lifetime of the
/// view. Distance/sort/date/filter pills still work as on the search tab.
struct PinnedShowsList: View {
    let apiClient: Client
    @StateObject private var model: ShowsListModel

    init(
        apiClient: Client,
        nearbyLocationController: NearbyLocationController,
        pinnedClubName: String? = nil,
        pinnedComedianName: String? = nil
    ) {
        self.apiClient = apiClient
        // Pinned detail views default to "Any date" — the shows endpoint already
        // returns upcoming-only when no date filter is set, and the prior
        // "Today" default left most comedian/club pages near-empty.
        _model = StateObject(wrappedValue: ShowsListModel(
            nearbyLocationController: nearbyLocationController,
            pinnedClubName: pinnedClubName,
            pinnedComedianName: pinnedComedianName,
            initialUseDateRange: false
        ))
    }

    var body: some View {
        ShowsListView(apiClient: apiClient, model: model)
    }
}
