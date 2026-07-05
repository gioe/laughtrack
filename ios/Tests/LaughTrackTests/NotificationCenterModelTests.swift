import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
@testable import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("NotificationCenterModel")
@MainActor
struct NotificationCenterModelTests {
    @Test("reload maps the feed into loaded items and captures the unread count")
    func reloadMapsFeed() async {
        let transport = NotificationsMockTransport(
            list: .init(data: .init(
                items: [
                    sampleItem(id: "c1:555", isUnread: true),
                    sampleItem(id: "c2:777", isUnread: false)
                ],
                unreadCount: 1,
                lastSeenAt: "2026-06-20T12:30:00.000Z"
            ))
        )
        let model = NotificationCenterModel()

        await model.reload(apiClient: makeClient(transport))

        guard case .loaded(let items) = model.phase else {
            Issue.record("Expected .loaded, got \(model.phase)")
            return
        }
        #expect(items.count == 2)
        #expect(items[0].id == "c1:555")
        #expect(items[0].title == "Taylor Tomlinson is performing near you")
        #expect(items[0].tap == .show(555))
        #expect(items[0].comedianImageURL == URL(string: "https://example.com/taylor.jpg"))
        #expect(items[0].channels == ["push", "email"])
        #expect(items[0].isUnread == true)
        #expect(items[0].sentAt != nil)
        #expect(model.unreadCount == 1)
    }

    @Test("an empty feed loads as an empty array (drives the empty state) with zero unread")
    func emptyFeed() async {
        let transport = NotificationsMockTransport(
            list: .init(data: .init(items: [], unreadCount: 0, lastSeenAt: nil))
        )
        let model = NotificationCenterModel()

        await model.reload(apiClient: makeClient(transport))

        #expect(model.phase == .loaded([]))
        #expect(model.unreadCount == 0)
    }

    @Test("reload filters notifications for shows that already happened")
    func reloadFiltersPastShows() async {
        let transport = NotificationsMockTransport(
            list: .init(data: .init(
                items: [
                    sampleItem(id: "c1:555", isUnread: true, showDate: "2000-01-01T02:00:00.000Z"),
                    sampleItem(id: "c2:777", isUnread: false, showDate: "2999-07-01T02:00:00.000Z")
                ],
                unreadCount: 1,
                lastSeenAt: nil
            ))
        )
        let model = NotificationCenterModel()

        await model.reload(apiClient: makeClient(transport))

        guard case .loaded(let items) = model.phase else {
            Issue.record("Expected .loaded, got \(model.phase)")
            return
        }
        #expect(items.map(\.id) == ["c2:777"])
    }

    @Test("sort recently sent orders newest sentAt first")
    func sortRecentlySent() {
        let items = sortableItems()

        #expect(NotificationSortOption.recentlySent.sorted(items).map(\.id) == [
            "newest-send",
            "same-send-sooner-show",
            "same-send-later-show",
            "oldest-send"
        ])
    }

    @Test("sort upcoming show orders earliest showDate first")
    func sortUpcomingShow() {
        let items = sortableItems()

        #expect(NotificationSortOption.upcomingShow.sorted(items).map(\.id) == [
            "oldest-send",
            "same-send-sooner-show",
            "same-send-later-show",
            "newest-send"
        ])
    }

    @Test("sort unread first groups unread notifications before sent time")
    func sortUnreadFirst() {
        let items = sortableItems()

        #expect(NotificationSortOption.unreadFirst.sorted(items).map(\.id) == [
            "same-send-sooner-show",
            "oldest-send",
            "newest-send",
            "same-send-later-show"
        ])
    }

    @Test("a 401 surfaces a sign-in failure message")
    func unauthorizedFailure() async {
        let transport = NotificationsMockTransport(listStatus: .unauthorized)
        let model = NotificationCenterModel()

        await model.reload(apiClient: makeClient(transport))

        guard case .failure(let message) = model.phase else {
            Issue.record("Expected .failure, got \(model.phase)")
            return
        }
        #expect(message.contains("Sign in"))
    }

    @Test("markSeen zeroes the unread badge count but leaves the per-row dots for the session")
    func markSeenClearsBadge() async {
        let transport = NotificationsMockTransport(
            list: .init(data: .init(
                items: [sampleItem(id: "c1:555", isUnread: true)],
                unreadCount: 1,
                lastSeenAt: nil
            )),
            seen: .init(data: .init(lastSeenAt: "2026-06-21T18:00:00.000Z"))
        )
        let model = NotificationCenterModel()
        let client = makeClient(transport)

        await model.reload(apiClient: client)
        #expect(model.unreadCount == 1)

        let ok = await model.markSeen(apiClient: client)

        #expect(ok == true)
        // Badge count zeroes immediately...
        #expect(model.unreadCount == 0)
        guard case .loaded(let items) = model.phase else {
            Issue.record("Expected .loaded, got \(model.phase)")
            return
        }
        // ...but the loaded rows keep their unread dots for this viewing session.
        #expect(items.contains { $0.isUnread })
    }

    @Test("NotificationCenterItem falls back gracefully and parses sentAt")
    func itemMapping() {
        let generated = Components.Schemas.NotificationItem(
            id: "c1:555",
            title: "X is performing near you",
            body: "The Store on Tuesday, June 30",
            comedianId: "c1",
            comedianName: "X",
            comedianImageUrl: "https://example.com/x.jpg",
            comedians: [.init(comedianId: "c1", comedianName: "X", comedianImageUrl: "https://example.com/x.jpg")],
            shows: [.init(showId: 555, subtitle: "The Store on Tuesday, June 30", showPageUrl: nil, showDate: nil, clubName: "The Store", city: "LA", state: "CA")],
            route: nil,
            channels: ["push"],
            sentAt: "2026-06-20T12:00:00.000Z",
            isUnread: true
        )

        let item = NotificationCenterItem(item: generated)

        #expect(item.tap == .show(555))
        #expect(item.comedianImageURL == URL(string: "https://example.com/x.jpg"))
        #expect(item.channels == ["push"])
        #expect(item.sentAt != nil)
        #expect(item.markedRead().isUnread == false)
    }

    @Test("a grouped entry with route=favorites taps into Favorites")
    func groupedItemTapsFavorites() async {
        let transport = NotificationsMockTransport(
            list: .init(data: .init(
                items: [groupedSampleItem(id: "run-1", isUnread: true)],
                unreadCount: 1,
                lastSeenAt: nil
            ))
        )
        let model = NotificationCenterModel()

        await model.reload(apiClient: makeClient(transport))

        guard case .loaded(let items) = model.phase else {
            Issue.record("Expected .loaded, got \(model.phase)")
            return
        }
        #expect(items.count == 1)
        #expect(items[0].tap == .favorites)
        #expect(items[0].title == "2 comedians you follow have shows near you")
    }

    @Test("NotificationCenterItem tolerates missing comedian image URL")
    func itemMappingWithoutImageURL() {
        let generated = Components.Schemas.NotificationItem(
            id: "c1:555",
            title: "X is performing near you",
            body: "The Store on Tuesday, June 30",
            comedianId: "c1",
            comedianName: "X",
            comedianImageUrl: "",
            comedians: [.init(comedianId: "c1", comedianName: "X", comedianImageUrl: "")],
            shows: [.init(showId: 555, subtitle: "The Store on Tuesday, June 30", showPageUrl: nil, showDate: nil, clubName: "The Store", city: "LA", state: "CA")],
            route: nil,
            channels: ["push"],
            sentAt: "2026-06-20T12:00:00.000Z",
            isUnread: true
        )

        let item = NotificationCenterItem(item: generated)

        #expect(item.comedianImageURL == nil)
        #expect(item.title == "X is performing near you")
    }

    @Test("row metadata omits delivery channels")
    func rowMetadataOmitsDeliveryChannels() {
        let item = NotificationCenterItem(
            id: "c1:555",
            title: "X is performing near you",
            body: "The Store on Tuesday, June 30",
            tap: .show(555),
            channels: ["push", "email"],
            comedianImageURL: URL(string: "https://example.com/x.jpg"),
            sentAt: Date(timeIntervalSince1970: 0),
            isUnread: true
        )

        #expect(item.metadataLabels(relativeSentAt: "2h ago") == ["2h ago"])
    }
}

@MainActor
private func makeClient(_ transport: NotificationsMockTransport) -> Client {
    Client(
        serverURL: URL(string: "https://example.com")!,
        configuration: .laughTrack,
        transport: transport
    )
}

private func sampleItem(
    id: String,
    isUnread: Bool,
    showDate: String? = "2999-07-01T02:00:00.000Z"
) -> Components.Schemas.NotificationItem {
    let comedianId = String(id.split(separator: ":").first ?? "")
    let showId = Int(id.split(separator: ":").last ?? "0") ?? 0
    return .init(
        id: id,
        title: "Taylor Tomlinson is performing near you",
        body: "The Comedy Store on Tuesday, June 30 at 7:00 pm PDT",
        comedianId: comedianId,
        comedianName: "Taylor Tomlinson",
        comedianImageUrl: "https://example.com/taylor.jpg",
        comedians: [
            .init(
                comedianId: comedianId,
                comedianName: "Taylor Tomlinson",
                comedianImageUrl: "https://example.com/taylor.jpg"
            )
        ],
        shows: [
            .init(
                showId: showId,
                subtitle: "The Comedy Store on Tuesday, June 30 at 7:00 pm PDT",
                showPageUrl: "https://laugh-track.com/show/\(showId)",
                showDate: showDate,
                clubName: "The Comedy Store",
                city: "Los Angeles",
                state: "CA"
            )
        ],
        route: nil,
        channels: ["push", "email"],
        sentAt: "2026-06-20T12:00:00.000Z",
        isUnread: isUnread
    )
}

/// A grouped entry: multiple shows across comedians, tapping into Favorites.
private func groupedSampleItem(id: String, isUnread: Bool) -> Components.Schemas.NotificationItem {
    .init(
        id: id,
        title: "2 comedians you follow have shows near you",
        body: "The Comedy Store, The Stand",
        comedianId: "c1",
        comedianName: "Taylor Tomlinson",
        comedianImageUrl: "https://example.com/taylor.jpg",
        comedians: [
            .init(comedianId: "c1", comedianName: "Taylor Tomlinson", comedianImageUrl: "https://example.com/taylor.jpg"),
            .init(comedianId: "c2", comedianName: "Ian Fidance", comedianImageUrl: "")
        ],
        shows: [
            .init(showId: 555, subtitle: "The Comedy Store on Tue, Jun 30", showPageUrl: nil, showDate: "2999-07-01T02:00:00.000Z", clubName: "The Comedy Store", city: "LA", state: "CA"),
            .init(showId: 777, subtitle: "The Stand on Sat, Jul 4", showPageUrl: nil, showDate: "2999-07-05T02:00:00.000Z", clubName: "The Stand", city: "NY", state: "NY")
        ],
        route: "favorites",
        channels: ["push"],
        sentAt: "2026-06-20T12:00:00.000Z",
        isUnread: isUnread
    )
}

private func sortableItems() -> [NotificationCenterItem] {
    [
        NotificationCenterItem(
            id: "oldest-send",
            title: "Oldest",
            body: "",
            tap: .show(1),
            channels: ["push"],
            showDate: NotificationCenterItem.parseTimestamp("2026-07-01T02:00:00.000Z"),
            sentAt: NotificationCenterItem.parseTimestamp("2026-06-20T10:00:00.000Z"),
            isUnread: true
        ),
        NotificationCenterItem(
            id: "same-send-later-show",
            title: "Later",
            body: "",
            tap: .show(2),
            channels: ["push"],
            showDate: NotificationCenterItem.parseTimestamp("2026-08-01T02:00:00.000Z"),
            sentAt: NotificationCenterItem.parseTimestamp("2026-06-20T12:00:00.000Z"),
            isUnread: false
        ),
        NotificationCenterItem(
            id: "same-send-sooner-show",
            title: "Sooner",
            body: "",
            tap: .show(3),
            channels: ["push"],
            showDate: NotificationCenterItem.parseTimestamp("2026-07-15T02:00:00.000Z"),
            sentAt: NotificationCenterItem.parseTimestamp("2026-06-20T12:00:00.000Z"),
            isUnread: true
        ),
        NotificationCenterItem(
            id: "newest-send",
            title: "Newest",
            body: "",
            tap: .show(4),
            channels: ["push"],
            showDate: NotificationCenterItem.parseTimestamp("2026-09-01T02:00:00.000Z"),
            sentAt: NotificationCenterItem.parseTimestamp("2026-06-20T13:00:00.000Z"),
            isUnread: false
        )
    ]
}

/// Serves the two notification operations. Behavior is fixed at init time;
/// `listStatus` lets a test force a non-200 on the list endpoint.
private struct NotificationsMockTransport: ClientTransport {
    enum ListStatus { case ok, unauthorized }

    let list: Components.Schemas.NotificationListResponse
    let listStatus: ListStatus
    let seen: Components.Schemas.NotificationsSeenResponse

    init(
        list: Components.Schemas.NotificationListResponse = .init(
            data: .init(items: [], unreadCount: 0, lastSeenAt: nil)
        ),
        listStatus: ListStatus = .ok,
        seen: Components.Schemas.NotificationsSeenResponse = .init(data: .init(lastSeenAt: nil))
    ) {
        self.list = list
        self.listStatus = listStatus
        self.seen = seen
    }

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let encoder = APIMockEncoder.make()
        switch operationID {
        case "getMeNotifications":
            if listStatus == .unauthorized {
                return (
                    HTTPResponse(status: .unauthorized, headerFields: [.contentType: "application/json"]),
                    HTTPBody(try encoder.encode(Components.Schemas.ErrorResponse(error: "unauthorized")))
                )
            }
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(list))
            )
        case "markMeNotificationsSeen":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(seen))
            )
        default:
            return (HTTPResponse(status: .notImplemented), nil)
        }
    }
}
