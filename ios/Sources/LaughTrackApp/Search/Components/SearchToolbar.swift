import SwiftUI

struct SearchToolbar<SortOption: View, FilterChipSet: View, DateScope: View, ResultCountLine: View>: View {
    @Environment(\.appTheme) private var theme

    private let sortOption: SortOption
    private let filterChipSet: FilterChipSet
    private let dateScope: DateScope
    private let resultCountLine: ResultCountLine

    init(
        @ViewBuilder sortOption: () -> SortOption,
        @ViewBuilder filterChipSet: () -> FilterChipSet,
        @ViewBuilder dateScope: () -> DateScope,
        @ViewBuilder resultCountLine: () -> ResultCountLine
    ) {
        self.sortOption = sortOption()
        self.filterChipSet = filterChipSet()
        self.dateScope = dateScope()
        self.resultCountLine = resultCountLine()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: theme.spacing.sm) {
                    sortOption
                    filterChipSet
                    dateScope
                }
                .fixedSize(horizontal: true, vertical: false)
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            resultCountLine
        }
    }
}

extension SearchToolbar where DateScope == EmptyView, ResultCountLine == EmptyView {
    init(
        @ViewBuilder sortOption: () -> SortOption,
        @ViewBuilder filterChipSet: () -> FilterChipSet
    ) {
        self.init(
            sortOption: sortOption,
            filterChipSet: filterChipSet,
            dateScope: { EmptyView() },
            resultCountLine: { EmptyView() }
        )
    }
}

extension SearchToolbar where SortOption == EmptyView, ResultCountLine == EmptyView {
    init(
        @ViewBuilder filterChipSet: () -> FilterChipSet,
        @ViewBuilder dateScope: () -> DateScope
    ) {
        self.init(
            sortOption: { EmptyView() },
            filterChipSet: filterChipSet,
            dateScope: dateScope,
            resultCountLine: { EmptyView() }
        )
    }
}

extension SearchToolbar where ResultCountLine == EmptyView {
    init(
        @ViewBuilder sortOption: () -> SortOption,
        @ViewBuilder filterChipSet: () -> FilterChipSet,
        @ViewBuilder dateScope: () -> DateScope
    ) {
        self.init(
            sortOption: sortOption,
            filterChipSet: filterChipSet,
            dateScope: dateScope,
            resultCountLine: { EmptyView() }
        )
    }
}

extension SearchToolbar where DateScope == EmptyView {
    init(
        @ViewBuilder sortOption: () -> SortOption,
        @ViewBuilder filterChipSet: () -> FilterChipSet,
        @ViewBuilder resultCountLine: () -> ResultCountLine
    ) {
        self.init(
            sortOption: sortOption,
            filterChipSet: filterChipSet,
            dateScope: { EmptyView() },
            resultCountLine: resultCountLine
        )
    }
}
