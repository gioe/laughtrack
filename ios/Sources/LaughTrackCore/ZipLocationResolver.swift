import Foundation

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
    private let baseURL: URL
    private let session: URLSession

    public init(baseURL: URL = AppConfiguration.apiBaseURL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    public func resolveLocation(forZip zipCode: String) async throws -> ResolvedNearbyLocation {
        guard let normalized = NearbyPreferenceStore.validZip(from: zipCode) else {
            throw ZipLocationLookupError.invalidZip
        }

        var components = URLComponents(
            url: baseURL.appendingPathComponent("api/v1/zip-lookup"),
            resolvingAgainstBaseURL: false
        )
        components?.queryItems = [URLQueryItem(name: "zip", value: normalized)]
        guard let url = components?.url else {
            throw ZipLocationLookupError.lookupFailed
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw ZipLocationLookupError.lookupFailed
        }

        guard let http = response as? HTTPURLResponse else {
            throw ZipLocationLookupError.lookupFailed
        }

        switch http.statusCode {
        case 200:
            let payload: Payload
            do {
                payload = try JSONDecoder().decode(Payload.self, from: data)
            } catch {
                throw ZipLocationLookupError.lookupFailed
            }
            return ResolvedNearbyLocation(
                zipCode: normalized,
                city: payload.city,
                state: payload.state
            )
        case 400:
            throw ZipLocationLookupError.invalidZip
        case 404:
            throw ZipLocationLookupError.unknownZip
        default:
            throw ZipLocationLookupError.lookupFailed
        }
    }

    private struct Payload: Decodable {
        let city: String
        let state: String
    }
}
