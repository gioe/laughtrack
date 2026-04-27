import Testing
import Foundation
import LaughTrackCore
import LaughTrackBridge
import LaughTrackAPIClient
import OpenAPIRuntime

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

    @Test("configure plus configureZipLocationResolver registers the full nearby-location stack")
    @MainActor
    func configureRegistersNearbyLocationStack() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)
        ServiceRegistration.configureZipLocationResolver(container, apiClient: makeStubClient())

        #expect(container.resolveOptional(NearbyPreferenceStore.self) != nil)
        #expect(container.resolveOptional((any NearbyLocationResolving).self) != nil)
        #expect(container.resolveOptional((any ZipLocationResolving).self) != nil)
        #expect(container.resolveOptional(NearbyLocationController.self) != nil)
    }

    @Test("NearbyPreferenceStore and NearbyLocationController are shared singletons across resolutions")
    @MainActor
    func nearbyLocationStackResolvesToSingletonInstances() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)
        ServiceRegistration.configureZipLocationResolver(container, apiClient: makeStubClient())

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

    @Test("configureZipLocationResolver registers ZipLocationResolving backed by APIZipLocationResolver")
    @MainActor
    func configureZipLocationResolverRegistersResolver() {
        let container = ServiceContainer()
        ServiceRegistration.configureZipLocationResolver(container, apiClient: makeStubClient())

        let resolved = container.resolveOptional((any ZipLocationResolving).self)
        #expect(resolved is APIZipLocationResolver)
    }

    @Test("configureOfflineQueue registers OfflineOperationQueue")
    @MainActor
    func configureOfflineQueueRegistersQueue() {
        let container = ServiceContainer()
        ServiceRegistration.configureOfflineQueue(container, apiClient: makeStubClient())
        let resolved = container.resolveOptional(OfflineOperationQueue<LaughTrackOfflineOperation>.self)
        #expect(resolved != nil)
    }
}

private func makeStubClient() -> Client {
    Client(
        serverURL: URL(string: "https://test.example.com")!,
        transport: StubClientTransport.alwaysSucceeds()
    )
}

// MARK: - AppConfiguration Tests

@Suite("AppConfiguration")
struct AppConfigurationTests {

    @Test("apiBaseURL points to the laughtrack host root")
    func apiBaseURL() {
        #expect(AppConfiguration.apiBaseURL == URL(string: "https://www.laugh-track.com")!)
    }
}
