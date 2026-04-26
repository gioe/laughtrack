import Foundation
import LaughTrackAPIClient

public enum ZipLocationLookupError: Error, Equatable {
    case invalidZip
    case unknownZip
    case lookupFailed
}

@MainActor
public protocol ZipLocationResolving: AnyObject {
    func resolveLocation(forZip zipCode: String) async throws -> ResolvedNearbyLocation
}

@MainActor
public final class APIZipLocationResolver: ZipLocationResolving {
    private let apiClient: Client

    public init(apiClient: Client) {
        self.apiClient = apiClient
    }

    public func resolveLocation(forZip zipCode: String) async throws -> ResolvedNearbyLocation {
        guard let normalized = NearbyPreferenceStore.validZip(from: zipCode) else {
            throw ZipLocationLookupError.invalidZip
        }

        let output: Operations.LookupZip.Output
        do {
            output = try await apiClient.lookupZip(.init(query: .init(zip: normalized)))
        } catch {
            throw ZipLocationLookupError.lookupFailed
        }

        switch output {
        case .ok(let ok):
            switch ok.body {
            case .json(let body):
                return ResolvedNearbyLocation(
                    zipCode: normalized,
                    city: body.city,
                    state: body.state
                )
            }
        case .badRequest:
            throw ZipLocationLookupError.invalidZip
        case .notFound:
            throw ZipLocationLookupError.unknownZip
        case .tooManyRequests, .undocumented:
            throw ZipLocationLookupError.lookupFailed
        }
    }
}
