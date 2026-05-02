import Testing
import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("Club row")
struct ClubRowTests {
    @Test("club row keeps location subtitle content")
    func clubRowKeepsLocationSubtitleContent() {
        let club = makeClub(city: "San Francisco", state: "CA", address: "444 Battery St")

        #expect(ClubRow.subtitle(for: club) == "San Francisco, CA")
    }

    @Test("club row falls back to address when city and state are absent")
    func clubRowFallsBackToAddress() {
        let club = makeClub(city: nil, state: nil, address: "444 Battery St")

        #expect(ClubRow.subtitle(for: club) == "444 Battery St")
    }

    @Test("club row keeps existing count metadata")
    func clubRowKeepsExistingCountMetadata() {
        let club = makeClub(activeComedianCount: 19, showCount: 8)

        #expect(ClubRow.metadata(for: club) == ["19 active comedians", "8 shows"])
    }

    private func makeClub(
        city: String? = "San Francisco",
        state: String? = "CA",
        address: String? = "444 Battery St",
        activeComedianCount: Int? = 19,
        showCount: Int? = 8
    ) -> Components.Schemas.ClubSearchItem {
        Components.Schemas.ClubSearchItem(
            id: 1,
            address: address,
            name: "Punch Line Comedy Club",
            zipCode: "94111",
            imageUrl: "",
            showCount: showCount,
            isFavorite: nil,
            city: city,
            state: state,
            phoneNumber: nil,
            socialData: nil,
            activeComedianCount: activeComedianCount,
            distanceMiles: nil
        )
    }
}
