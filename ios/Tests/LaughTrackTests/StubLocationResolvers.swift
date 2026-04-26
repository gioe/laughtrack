import Foundation
@testable import LaughTrackCore

@MainActor
final class StubNearbyLocationResolver: NearbyLocationResolving {
    func requestCurrentZip() async throws -> String {
        throw NearbyLocationError.unavailable
    }
}

@MainActor
final class StubZipLocationResolver: ZipLocationResolving {
    var result: Result<ResolvedNearbyLocation, Error>

    init(result: Result<ResolvedNearbyLocation, Error> = .failure(ZipLocationLookupError.unknownZip)) {
        self.result = result
    }

    func resolveLocation(forZip zipCode: String) async throws -> ResolvedNearbyLocation {
        try result.get()
    }
}
