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

// Podcasts sort separately because "popularity" is meaningless for episodic
// content — the meaningful axis is episode count (web labels this "Most
// Episodes" / show_count_desc). Aligned with web's getSortOptionsForEntityType.
enum PodcastSortOption: String, CaseIterable, Identifiable {
    case mostEpisodes = "show_count_desc"
    case fewestEpisodes = "show_count_asc"
    case alphabetical = "name_asc"
    case reverseAlphabetical = "name_desc"

    var id: String { rawValue }

    var title: String {
        switch self {
        case .mostEpisodes:
            return "Most episodes"
        case .fewestEpisodes:
            return "Fewest episodes"
        case .alphabetical:
            return "A-Z"
        case .reverseAlphabetical:
            return "Z-A"
        }
    }
}

// Clubs sort separately because the web default is "Most Active"
// (total_shows_desc) — popularity data is sparse for venues, so clubs lead
// with show-count activity. Kept aligned with web's getSortOptionsForEntityType.
enum ClubSortOption: String, CaseIterable, Identifiable {
    case mostActive = "total_shows_desc"
    case leastActive = "total_shows_asc"
    case mostPopular = "popularity_desc"
    case leastPopular = "popularity_asc"
    case alphabetical = "name_asc"
    case reverseAlphabetical = "name_desc"

    var id: String { rawValue }

    var title: String {
        switch self {
        case .mostActive:
            return "Most active"
        case .leastActive:
            return "Least active"
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

struct ShowsListQuery: Hashable {
    let comedian: String
    let club: String
    let filters: [String]
    let zip: String
    let dateRange: DateRangeFilter
    let distance: ShowDistanceOption
    let sort: ShowSortOption

    var fromString: String? {
        guard dateRange.isActive else { return nil }
        return ShowFormatting.apiDate(dateRange.from)
    }

    var toString: String? {
        guard dateRange.isActive else { return nil }
        return ShowFormatting.apiDate(max(dateRange.to, dateRange.from))
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
        dateRange.isActive ||
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
    /// API sort raw value (e.g. "popularity_desc", "total_shows_desc"). Stored
    /// as `String` so Comedians (`PrimitiveSortOption`) and Clubs
    /// (`ClubSortOption`) can share this query envelope without coupling to a
    /// single enum.
    let sort: String
    let includeEmpty: Bool

    init(
        text: String,
        filters: [String],
        sort: String,
        includeEmpty: Bool = false
    ) {
        self.text = text
        self.filters = filters
        self.sort = sort
        self.includeEmpty = includeEmpty
    }

    var filtersParam: String? {
        guard !filters.isEmpty else { return nil }
        return filters.joined(separator: ",")
    }

    var cacheKey: String {
        [
            "text=\(text)",
            "filters=\(filtersParam ?? "")",
            "sort=\(sort)",
            "includeEmpty=\(includeEmpty)",
        ].joined(separator: "|")
    }
}

struct DiscoveryLoadTaskKey<Query: Hashable>: Hashable {
    let isActive: Bool
    let query: Query
}
