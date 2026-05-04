import Foundation
import LaughTrackAPIClient

actor PersistentMainPageCache {
    struct CachedValue<Value: Sendable>: Sendable {
        let value: Value
        let expiresAt: Date
    }

    static let shared = PersistentMainPageCache()

    private struct Entry<Value: Codable>: Codable {
        let value: Value
        let expiresAt: Date
    }

    private let directory: URL
    private let fileManager: FileManager
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    init(
        directory: URL = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)
            .first!
            .appendingPathComponent("LaughTrackMainPageCache", isDirectory: true),
        fileManager: FileManager = .default
    ) {
        self.directory = directory
        self.fileManager = fileManager
    }

    func setHomeFeed(_ feed: Components.Schemas.HomeFeed, zipCode: String?, ttl: TimeInterval) {
        set(feed, fileName: "home-feed-\(fileNameComponent(zipCode ?? "default"))", ttl: ttl)
    }

    func getHomeFeed(zipCode: String?) -> Components.Schemas.HomeFeed? {
        getCachedHomeFeed(zipCode: zipCode)?.value
    }

    func getCachedHomeFeed(zipCode: String?) -> CachedValue<Components.Schemas.HomeFeed>? {
        get(fileName: "home-feed-\(fileNameComponent(zipCode ?? "default"))")
    }

    func setFavoriteShows(_ shows: [Components.Schemas.Show], requestKey: String, ttl: TimeInterval) {
        set(shows, fileName: "favorite-shows-\(fileNameComponent(requestKey))", ttl: ttl)
    }

    func getFavoriteShows(requestKey: String) -> [Components.Schemas.Show]? {
        getCachedFavoriteShows(requestKey: requestKey)?.value
    }

    func getCachedFavoriteShows(requestKey: String) -> CachedValue<[Components.Schemas.Show]>? {
        get(fileName: "favorite-shows-\(fileNameComponent(requestKey))")
    }

    private func set<Value: Codable & Sendable>(_ value: Value, fileName: String, ttl: TimeInterval) {
        let entry = Entry(value: value, expiresAt: Date().addingTimeInterval(ttl))

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
            guard Date() < entry.expiresAt else {
                try? fileManager.removeItem(at: url)
                return nil
            }
            return CachedValue(value: entry.value, expiresAt: entry.expiresAt)
        } catch {
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
