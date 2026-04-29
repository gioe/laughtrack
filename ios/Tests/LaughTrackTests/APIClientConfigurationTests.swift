import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackCore

@Suite("API client configuration")
struct APIClientConfigurationTests {
    @Test("LaughTrack configuration decodes fractional-second show dates")
    func configurationDecodesFractionalSecondDates() async throws {
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: FractionalDateTransport()
        )

        let output = try await client.searchShows(.init(query: .init(size: 1)))
        guard case .ok(let ok) = output else {
            Issue.record("Expected searchShows to return 200")
            return
        }

        let response = try ok.body.json
        #expect(response.data.first?.id == 854607)
        #expect(response.data.first?.date.timeIntervalSince1970 == 1_779_849_000)
    }

    @Test("response decode errors classify separately from network errors")
    func decodeErrorsClassifySeparatelyFromNetworkErrors() async {
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            transport: FractionalDateTransport()
        )

        do {
            _ = try await client.searchShows(.init(query: .init(size: 1)))
            Issue.record("Expected default client configuration to reject fractional-second dates")
        } catch {
            let failure = classifyRequestError(
                error,
                context: "the shows search service",
                networkMessage: "Network fallback"
            )
            #expect(failure.defaultTitle == "Data issue")
            #expect(failure.message == "LaughTrack reached the shows search service, but could not read the response. Please try again.")
        }
    }
}

private struct FractionalDateTransport: ClientTransport {
    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let body = """
        {
          "data": [
            {
              "id": 854607,
              "date": "2026-05-27T02:30:00.000Z",
              "name": "Too Hot Tuesdays",
              "clubName": "Flappers Comedy Club And Restaurant Burbank",
              "imageUrl": "/placeholders/club-placeholder.svg",
              "soldOut": false,
              "lineup": [],
              "tickets": []
            }
          ],
          "total": 1,
          "filters": [],
          "zipCapTriggered": false
        }
        """

        return (
            HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
            HTTPBody(body)
        )
    }
}
