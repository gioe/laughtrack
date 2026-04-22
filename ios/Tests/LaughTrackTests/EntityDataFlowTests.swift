import Testing
@testable import LaughTrackApp

@Suite("Entity data flow")
@MainActor
struct EntityDataFlowTests {
    @Test("entity navigation targets map to the expected app routes")
    func navigationTargetsMapToRoutes() {
        #expect(EntityNavigationTarget.show(7).route == .showDetail(7))
        #expect(EntityNavigationTarget.comedian(8).route == .comedianDetail(8))
        #expect(EntityNavigationTarget.club(9).route == .clubDetail(9))
    }

    @Test("search model standardizes reload and load more pagination")
    func searchModelReloadAndLoadMore() async {
        let model = EntitySearchModel<String, Int>()

        await model.reload(query: "clubs") { page, query in
            #expect(page == 0)
            #expect(query == "clubs")
            return .success(.init(items: [10, 11], total: 4))
        }

        switch model.phase {
        case .success(let page):
            #expect(page.items == [10, 11])
            #expect(page.total == 4)
            #expect(page.page == 0)
        default:
            Issue.record("Expected reload to finish in a success phase")
        }

        await model.loadMore(query: "clubs") { page, query in
            #expect(page == 1)
            #expect(query == "clubs")
            return .success(.init(items: [12, 13], total: 4))
        }

        switch model.phase {
        case .success(let page):
            #expect(page.items == [10, 11, 12, 13])
            #expect(page.total == 4)
            #expect(page.page == 1)
        default:
            Issue.record("Expected loadMore to preserve and append results")
        }
    }

    @Test("search model keeps prior results and surfaces pagination failures")
    func searchModelKeepsResultsOnPaginationFailure() async {
        let model = EntitySearchModel<String, Int>()

        await model.reload(query: "shows") { _, _ in
            .success(.init(items: [1, 2], total: 3))
        }

        await model.loadMore(query: "shows") { _, _ in
            .failure("Timed out")
        }

        switch model.phase {
        case .success(let page):
            #expect(page.items == [1, 2])
            #expect(page.page == 0)
        default:
            Issue.record("Expected prior success page to remain after pagination failure")
        }

        #expect(model.paginationMessage == "Timed out")
    }

    @Test("detail model only performs its first automatic load once")
    func detailModelOnlyLoadsOnceWhenIdle() async {
        let model = EntityDetailModel<Int>()
        var callCount = 0

        await model.loadIfNeeded {
            callCount += 1
            return .success(42)
        }

        await model.loadIfNeeded {
            callCount += 1
            return .success(99)
        }

        #expect(callCount == 1)

        switch model.phase {
        case .success(let value):
            #expect(value == 42)
        default:
            Issue.record("Expected detail model to hold onto its first loaded value")
        }
    }
}
