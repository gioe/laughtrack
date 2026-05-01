import Foundation

enum ShowDistanceOption: Int, CaseIterable, Identifiable {
    case nearby = 10
    case city = 25
    case regional = 50
    case roadTrip = 100

    var id: Int { rawValue }

    var title: String {
        "\(rawValue) mi"
    }

    static func from(distanceMiles: Int) -> Self {
        Self(rawValue: distanceMiles) ?? .city
    }
}

enum ShowSortOption: String, CaseIterable, Identifiable {
    case earliest = "date_asc"
    case latest = "date_desc"
    case popular = "popularity_desc"
    case budget = "price_asc"
    case premium = "price_desc"

    var id: String { rawValue }

    var title: String {
        switch self {
        case .earliest:
            return "Earliest"
        case .latest:
            return "Latest"
        case .popular:
            return "Popular"
        case .budget:
            return "Low price"
        case .premium:
            return "High price"
        }
    }
}

enum PrimitiveSortOption: String, CaseIterable, Identifiable {
    case mostPopular = "popularity_desc"
    case leastPopular = "popularity_asc"
    case alphabetical = "name_asc"
    case reverseAlphabetical = "name_desc"

    var id: String { rawValue }

    var title: String {
        switch self {
        case .mostPopular:
            return "Most popular"
        case .leastPopular:
            return "Least popular"
        case .alphabetical:
            return "A-Z"
        case .reverseAlphabetical:
            return "Z-A"
        }
    }
}

struct ShowsDiscoveryQuery: Hashable {
    let comedian: String
    let club: String
    let filters: [String]
    let zip: String
    let useDateRange: Bool
    let from: Date
    let to: Date
    let distance: ShowDistanceOption
    let sort: ShowSortOption

    var fromString: String? {
        guard useDateRange else { return nil }
        return ShowFormatting.apiDate(from)
    }

    var toString: String? {
        guard useDateRange else { return nil }
        return ShowFormatting.apiDate(to)
    }

    var sanitizedZip: String? {
        let digits = zip.filter(\.isNumber)
        guard digits.count == 5 else { return nil }
        return digits
    }

    var filtersParam: String? {
        guard !filters.isEmpty else { return nil }
        return filters.joined(separator: ",")
    }

    var hasActiveFilters: Bool {
        !comedian.isEmpty ||
        !club.isEmpty ||
        !filters.isEmpty ||
        sanitizedZip != nil ||
        useDateRange ||
        sort != .earliest
    }

    var cacheKey: String {
        [
            "comedian=\(comedian)",
            "club=\(club)",
            "filters=\(filtersParam ?? "")",
            "zip=\(sanitizedZip ?? "")",
            "from=\(fromString ?? "")",
            "to=\(toString ?? "")",
            "distance=\(distance.rawValue)",
            "sort=\(sort.rawValue)",
        ].joined(separator: "|")
    }
}

struct PrimitiveDiscoveryQuery: Hashable {
    let text: String
    let filters: [String]
    let sort: PrimitiveSortOption

    var filtersParam: String? {
        guard !filters.isEmpty else { return nil }
        return filters.joined(separator: ",")
    }

    var cacheKey: String {
        [
            "text=\(text)",
            "filters=\(filtersParam ?? "")",
            "sort=\(sort.rawValue)",
        ].joined(separator: "|")
    }
}

struct DiscoveryLoadTaskKey<Query: Hashable>: Hashable {
    let isActive: Bool
    let query: Query
}
