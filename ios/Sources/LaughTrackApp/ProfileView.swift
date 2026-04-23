import SwiftUI
import LaughTrackAPIClient
import LaughTrackCore

@MainActor
struct ProfileView: View {
    let apiClient: Client
    let signedOutMessage: String?

    @StateObject private var nearbyPreferenceStore: NearbyPreferenceStore

    init(
        apiClient: Client,
        signedOutMessage: String?,
        nearbyPreferenceStore: NearbyPreferenceStore? = nil
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        _nearbyPreferenceStore = StateObject(
            wrappedValue: nearbyPreferenceStore ?? NearbyPreferenceStore()
        )
    }

    var body: some View {
        SettingsView(
            apiClient: apiClient,
            signedOutMessage: signedOutMessage,
            nearbyPreferenceStore: nearbyPreferenceStore
        )
    }
}
