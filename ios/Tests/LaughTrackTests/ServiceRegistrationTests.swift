import Testing
import Foundation
import LaughTrackCore
import LaughTrackBridge
import LaughTrackAPIClient
import OpenAPIRuntime
import HTTPTypes

// MARK: - Mock Transport

private struct MockTransport: ClientTransport {
    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        (HTTPResponse(status: .ok), nil)
    }
}

// MARK: - ServiceRegistration Tests

@Suite("ServiceRegistration")
struct ServiceRegistrationTests {

    @Test("configure registers NetworkMonitorProtocol")
    @MainActor
    func configureRegistersNetworkMonitor() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)
        let resolved = container.resolveOptional(NetworkMonitorProtocol.self)
        #expect(resolved != nil)
    }

    @Test("configure registers SecureStorageProtocol")
    @MainActor
    func configureRegistersSecureStorage() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)
        let resolved = container.resolveOptional(SecureStorageProtocol.self)
        #expect(resolved != nil)
    }

    @Test("configure registers ToastManager")
    @MainActor
    func configureRegistersToastManager() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)
        let resolved = container.resolveOptional(ToastManager.self)
        #expect(resolved != nil)
    }

    @Test("configure registers ImageCache")
    @MainActor
    func configureRegistersImageCache() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)
        let resolved = container.resolveOptional(ImageCache.self)
        #expect(resolved != nil)
    }

    @Test("configure registers AppStateStorageProtocol")
    @MainActor
    func configureRegistersAppStateStorage() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)
        let resolved = container.resolveOptional(AppStateStorageProtocol.self)
        #expect(resolved != nil)
    }

    @Test("configure registers DataCache with LaughTrackCacheKey")
    @MainActor
    func configureRegistersDataCache() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)
        let resolved = container.resolveOptional(DataCache<LaughTrackCacheKey>.self)
        #expect(resolved != nil)
    }

    @Test("configure registers all six expected services")
    @MainActor
    func configureRegistersAllServices() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)

        #expect(container.resolveOptional(NetworkMonitorProtocol.self) != nil)
        #expect(container.resolveOptional(SecureStorageProtocol.self) != nil)
        #expect(container.resolveOptional(ToastManager.self) != nil)
        #expect(container.resolveOptional(ImageCache.self) != nil)
        #expect(container.resolveOptional(AppStateStorageProtocol.self) != nil)
        #expect(container.resolveOptional(DataCache<LaughTrackCacheKey>.self) != nil)
    }

    @Test("configure registers NearbyPreferenceStore, NearbyLocationResolving, and NearbyLocationController")
    @MainActor
    func configureRegistersNearbyLocationStack() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)

        #expect(container.resolveOptional(NearbyPreferenceStore.self) != nil)
        #expect(container.resolveOptional((any NearbyLocationResolving).self) != nil)
        #expect(container.resolveOptional(NearbyLocationController.self) != nil)
    }

    @Test("NearbyPreferenceStore and NearbyLocationController are shared singletons across resolutions")
    @MainActor
    func nearbyLocationStackResolvesToSingletonInstances() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)

        let storeA = container.resolve(NearbyPreferenceStore.self)
        let storeB = container.resolve(NearbyPreferenceStore.self)
        let controllerA = container.resolve(NearbyLocationController.self)
        let controllerB = container.resolve(NearbyLocationController.self)
        let resolverA = container.resolve((any NearbyLocationResolving).self)
        let resolverB = container.resolve((any NearbyLocationResolving).self)

        #expect(storeA === storeB)
        #expect(controllerA === controllerB)
        #expect(resolverA === resolverB)
    }

    @Test("configureOfflineQueue registers OfflineOperationQueue")
    @MainActor
    func configureOfflineQueueRegistersQueue() {
        let container = ServiceContainer()
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            transport: MockTransport()
        )
        ServiceRegistration.configureOfflineQueue(container, apiClient: client)
        let resolved = container.resolveOptional(OfflineOperationQueue<LaughTrackOfflineOperation>.self)
        #expect(resolved != nil)
    }
}

// MARK: - AppConfiguration Tests

@Suite("AppConfiguration")
struct AppConfigurationTests {

    @Test("apiBaseURL points to the laughtrack host root")
    func apiBaseURL() {
        #expect(AppConfiguration.apiBaseURL == URL(string: "https://www.laugh-track.com")!)
    }
}
