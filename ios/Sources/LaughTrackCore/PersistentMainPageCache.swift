import Foundation
import LaughTrackAPIClient

public extension Components.Schemas.HomeFeed {
    /// The location-scoped portion that is safe to reuse across accounts.
    var publicCacheSlice: Self {
        var feed = self
        feed.followedComedianShows = []
        return feed
    }
}

public actor PersistentMainPageCache {
    public struct CachedValue<Value: Sendable>: Sendable {
        public let value: Value
        public let expiresAt: Date

        public init(value: Value, expiresAt: Date) {
            self.value = value
            self.expiresAt = expiresAt
        }
    }

    public static let shared = PersistentMainPageCache()

    /// Stamp persisted entries with the app build number. Entries are decoded
    /// into generated OpenAPI types (`Components.Schemas.*`); when a new build
    /// changes the home-feed schema, a blob written by a prior build may no
    /// longer decode — or worse, decode into a semantically wrong value. Keying
    /// on the build number means any entry from a different build is treated as
    /// a miss and refetched, instead of bleeding stale data into the Discover
    /// rails (TASK-2919). CFBundleVersion changes on every build, so this also
    /// covers schema changes that happen to remain decode-compatible.
    public static var defaultSchemaVersion: String {
        (Bundle.main.infoDictionary?["CFBundleVersion"] as? String) ?? "0"
    }

    private struct Entry<Value: Codable>: Codable {
        let value: Value
        let expiresAt: Date
        // Optional so a legacy entry written before this field existed decodes
        // successfully and is then invalidated by the version mismatch below
        // (rather than being silently treated as current).
        let schemaVersion: String?
    }

    private let directory: URL
    private let fileManager: FileManager
    private let schemaVersion: String
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    public init(
        directory: URL = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)
            .first!
            .appendingPathComponent("LaughTrackMainPageCache", isDirectory: true),
        fileManager: FileManager = .default,
        schemaVersion: String = PersistentMainPageCache.defaultSchemaVersion
    ) {
        self.directory = directory
        self.fileManager = fileManager
        self.schemaVersion = schemaVersion
        Self.purgeOrphanedNearbyShowsFiles(in: directory, fileManager: fileManager)
    }

    private static func purgeOrphanedNearbyShowsFiles(in directory: URL, fileManager: FileManager) {
        guard let contents = try? fileManager.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        ) else { return }
        for url in contents
        where url.lastPathComponent.hasPrefix("nearby-shows-") && url.pathExtension == "json" {
            try? fileManager.removeItem(at: url)
        }
    }

    public func setHomeFeed(
        _ feed: Components.Schemas.HomeFeed,
        zipCode: String?,
        distanceMiles: Int? = nil,
        ttl: TimeInterval
    ) {
        set(
            feed.publicCacheSlice,
            fileName: homeFeedFileName(zipCode: zipCode, distanceMiles: distanceMiles),
            ttl: ttl
        )
    }

    public func getHomeFeed(zipCode: String?, distanceMiles: Int? = nil) -> Components.Schemas.HomeFeed? {
        getCachedHomeFeed(zipCode: zipCode, distanceMiles: distanceMiles)?.value
    }

    public func getCachedHomeFeed(
        zipCode: String?,
        distanceMiles: Int? = nil
    ) -> CachedValue<Components.Schemas.HomeFeed>? {
        guard let cached: CachedValue<Components.Schemas.HomeFeed> = get(
            fileName: homeFeedFileName(zipCode: zipCode, distanceMiles: distanceMiles)
        ) else { return nil }
        return CachedValue(
            value: cached.value.publicCacheSlice,
            expiresAt: cached.expiresAt
        )
    }

    public func setFavoriteShows(_ shows: [Components.Schemas.Show], requestKey: String, ttl: TimeInterval) {
        set(shows, fileName: "favorite-shows-\(fileNameComponent(requestKey))", ttl: ttl)
    }

    public func getFavoriteShows(requestKey: String) -> [Components.Schemas.Show]? {
        getCachedFavoriteShows(requestKey: requestKey)?.value
    }

    public func getCachedFavoriteShows(requestKey: String) -> CachedValue<[Components.Schemas.Show]>? {
        get(fileName: "favorite-shows-\(fileNameComponent(requestKey))")
    }

    public func setSavedShows(
        _ response: Components.Schemas.SavedShowListResponse,
        accountId: String,
        period: String,
        page: Int,
        size: Int,
        ttl: TimeInterval
    ) {
        set(
            response,
            fileName: savedShowsFileName(
                accountId: accountId,
                period: period,
                page: page,
                size: size
            ),
            ttl: ttl
        )
    }

    public func getSavedShows(
        accountId: String,
        period: String,
        page: Int,
        size: Int
    ) -> Components.Schemas.SavedShowListResponse? {
        get(
            fileName: savedShowsFileName(
                accountId: accountId,
                period: period,
                page: page,
                size: size
            )
        )?.value
    }

    public func removeSavedShows(accountId: String) {
        let prefix = "saved-shows-\(fileNameComponent(accountId))-"
        guard let contents = try? fileManager.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        ) else { return }

        for url in contents where url.lastPathComponent.hasPrefix(prefix) {
            try? fileManager.removeItem(at: url)
        }
    }

    private func homeFeedFileName(zipCode: String?, distanceMiles: Int?) -> String {
        let zipComponent = zipCode ?? "default"
        guard let distanceMiles else {
            return "home-feed-\(fileNameComponent(zipComponent))"
        }
        return "home-feed-\(fileNameComponent("\(zipComponent)-\(distanceMiles)mi"))"
    }

    private func savedShowsFileName(
        accountId: String,
        period: String,
        page: Int,
        size: Int
    ) -> String {
        "saved-shows-\(fileNameComponent(accountId))-\(fileNameComponent(period))-p\(page)-s\(size)"
    }

    private func set<Value: Codable & Sendable>(_ value: Value, fileName: String, ttl: TimeInterval) {
        let entry = Entry(
            value: value,
            expiresAt: Date().addingTimeInterval(ttl),
            schemaVersion: schemaVersion
        )

        do {
            try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
            let data = try encoder.encode(entry)
            try data.write(to: fileURL(fileName: fileName), options: [.atomic])
        } catch {
            return
        }
    }

    private func get<Value: Codable & Sendable>(fileName: String) -> CachedValue<Value>? {
        let url = fileURL(fileName: fileName)

        do {
            let data = try Data(contentsOf: url)
            let entry = try decoder.decode(Entry<Value>.self, from: data)
            // A blob written by a different build may decode into a semantically
            // stale value; treat a version mismatch (or a legacy entry with no
            // stamped version) as a miss and delete it so it is refetched.
            guard entry.schemaVersion == schemaVersion else {
                try? fileManager.removeItem(at: url)
                return nil
            }
            guard Date() < entry.expiresAt else {
                try? fileManager.removeItem(at: url)
                return nil
            }
            return CachedValue(value: entry.value, expiresAt: entry.expiresAt)
        } catch {
            // Undecodable entry (corrupt, or a prior build's incompatible
            // schema): delete it so a stale blob never blocks the feed, then
            // report a miss so the caller refetches from the network.
            try? fileManager.removeItem(at: url)
            return nil
        }
    }

    private func fileURL(fileName: String) -> URL {
        directory.appendingPathComponent("\(fileName).json", isDirectory: false)
    }

    private func fileNameComponent(_ value: String) -> String {
        let allowedCharacters = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-_"))
        let scalars = value.unicodeScalars.map { scalar in
            allowedCharacters.contains(scalar) ? Character(scalar) : "_"
        }
        return String(scalars)
    }
}
