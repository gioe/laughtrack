import Testing
@testable import LaughTrackApp

@Suite("Detail hero layout")
struct DetailHeroLayoutTests {
    @Test("detail hero keeps media landscape and below most of a phone viewport")
    func detailHeroUsesCompactLandscapeMedia() {
        #expect(DetailHeroLayout.imageAspectRatio >= 1.45)
        #expect(DetailHeroLayout.maximumMediaHeight <= 280)
        #expect(DetailHeroLayout.mediaHeight(forWidth: 390) <= 280)
    }

    @Test("detail hero action layout stays compact enough for title clearance")
    func detailHeroActionLayoutIsCompact() {
        #expect(DetailHeroLayout.actionDiameter <= 40)
        #expect(DetailHeroLayout.actionLabelVerticalGap <= 3)
        #expect(DetailHeroLayout.contentSpacingWithActions <= 8)
    }

    @Test("club detail hero omits subtitle copy")
    func clubDetailHeroOmitsSubtitleCopy() {
        #expect(ClubDetailHeroPresentation.subtitle(upcomingShowCount: 8, zipCode: "10012") == nil)
        #expect(ClubDetailHeroPresentation.subtitle(upcomingShowCount: 0, zipCode: "10012") == nil)
    }
}
