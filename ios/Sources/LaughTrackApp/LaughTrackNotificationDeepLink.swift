import Foundation

enum LaughTrackNotificationDeepLink {
    static func route(from userInfo: [AnyHashable: Any]) -> AppRoute? {
        // Grouped-push tap → Favorites tab (renders upcoming shows from followed
        // comedians). Checked before showId, which grouped pushes still carry as
        // the fallback for older builds that predate this key.
        if let route = userInfo["route"] as? String,
           route.trimmingCharacters(in: .whitespacesAndNewlines) == "favorites" {
            return .library(showIDs(from: userInfo["showIds"]))
        }
        if let showID = integerValue(userInfo["showId"]) {
            return .showDetail(showID)
        }
        if let urlString = userInfo["url"] as? String,
           let url = URL(string: urlString) {
            return route(from: url)
        }
        return nil
    }

    static func route(from url: URL) -> AppRoute? {
        if let showID = showIDFromQuery(url) {
            return .showDetail(showID)
        }

        let components = pathComponents(for: url)
        guard let showIndex = components.firstIndex(where: { $0 == "show" || $0 == "shows" }),
              components.indices.contains(showIndex + 1),
              let showID = Int(components[showIndex + 1])
        else {
            return nil
        }
        return .showDetail(showID)
    }

    /// Parse a comma-joined "555,777" show-id string (grouped-push context).
    private static func showIDs(from raw: Any?) -> [Int] {
        guard let string = raw as? String else { return [] }
        return string
            .split(separator: ",")
            .compactMap { Int($0.trimmingCharacters(in: .whitespaces)) }
    }

    private static func integerValue(_ raw: Any?) -> Int? {
        if let value = raw as? Int {
            return value
        }
        if let value = raw as? NSNumber {
            return value.intValue
        }
        if let value = raw as? String {
            return Int(value.trimmingCharacters(in: .whitespacesAndNewlines))
        }
        return nil
    }

    private static func showIDFromQuery(_ url: URL) -> Int? {
        URLComponents(url: url, resolvingAgainstBaseURL: false)?
            .queryItems?
            .first(where: { $0.name == "showId" || $0.name == "showID" })?
            .value
            .flatMap(Int.init)
    }

    private static func pathComponents(for url: URL) -> [String] {
        var components = url.pathComponents.filter { $0 != "/" }
        if let host = url.host, url.scheme?.lowercased() == "laughtrack" {
            components.insert(host, at: 0)
        }
        return components.map { $0.lowercased() }
    }
}

enum LaughTrackNotificationMedia {
    static func imageURL(from userInfo: [AnyHashable: Any]) -> URL? {
        stringValue(userInfo["imageUrl"])
            .flatMap(URL.init(string:))
    }

    private static func stringValue(_ raw: Any?) -> String? {
        guard let value = raw as? String else { return nil }
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}
