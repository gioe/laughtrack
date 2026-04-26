import Foundation
@testable import LaughTrackCore

@MainActor
final class FailingNearbyLocationResolver: NearbyLocationResolving {
    func requestCurrentZip() async throws -> String {
        throw NearbyLocationError.unavailable
    }
}

@MainActor
final class FailingZipLocationResolver: ZipLocationResolving {
    func resolveLocation(forZip zipCode: String) async throws -> ResolvedNearbyLocation {
        throw ZipLocationLookupError.unknownZip
    }
}
