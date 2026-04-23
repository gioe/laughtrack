import SwiftUI
import LaughTrackAPIClient
import LaughTrackCore

@MainActor
struct ProfileView: View {
    let apiClient: Client
    let signedOutMessage: String?
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore

    init(
        apiClient: Client,
        signedOutMessage: String?,
        nearbyPreferenceStore: NearbyPreferenceStore
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self._nearbyPreferenceStore = ObservedObject(wrappedValue: nearbyPreferenceStore)
    }

    var body: some View {
        SettingsView(
            apiClient: apiClient,
            signedOutMessage: signedOutMessage,
            nearbyPreferenceStore: nearbyPreferenceStore
        )
    }
}
