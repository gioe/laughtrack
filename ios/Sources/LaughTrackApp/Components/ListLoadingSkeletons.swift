import SwiftUI

struct ShowsListSkeleton: View {
    @Environment(\.appTheme) private var theme

    var includesHero: Bool = false
    var rowCount: Int = 5

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let block = laughTrack.colors.surfaceMuted

        VStack(alignment: .leading, spacing: theme.spacing.md) {
            if includesHero {
                RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                    .fill(block)
                    .frame(height: 280)
            }

            VStack(spacing: 10) {
                ForEach(0..<rowCount, id: \.self) { _ in
                    VStack(alignment: .leading, spacing: theme.spacing.sm) {
                        HStack(alignment: .top, spacing: theme.spacing.md) {
                            VStack(alignment: .center, spacing: 3) {
                                RoundedRectangle(cornerRadius: 4)
                                    .fill(block)
                                    .frame(width: 32, height: 9)
                                RoundedRectangle(cornerRadius: 6)
                                    .fill(block)
                                    .frame(width: 38, height: 26)
                                RoundedRectangle(cornerRadius: 4)
                                    .fill(block)
                                    .frame(width: 44, height: 11)
                            }
                            .frame(width: 64)

                            VStack(alignment: .leading, spacing: 7) {
                                RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 190, height: 16)
                                RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 138, height: 12)
                                RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 96, height: 12)
                                HStack(spacing: theme.spacing.xs) {
                                    RoundedRectangle(cornerRadius: 8).fill(block).frame(width: 58, height: 18)
                                    RoundedRectangle(cornerRadius: 8).fill(block).frame(width: 66, height: 18)
                                }
                            }
                            Spacer(minLength: 0)
                            RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 8, height: 14)
                        }

                        HStack(spacing: theme.spacing.sm) {
                            ForEach(0..<3, id: \.self) { _ in
                                VStack(spacing: 4) {
                                    Circle()
                                        .fill(block)
                                        .frame(width: 44, height: 44)
                                    RoundedRectangle(cornerRadius: 4)
                                        .fill(block)
                                        .frame(height: 10)
                                }
                                .frame(maxWidth: .infinity)
                            }
                        }
                    }
                    .frame(maxWidth: .infinity, minHeight: 124, alignment: .leading)
                    .padding(.horizontal, laughTrack.browseDensity.compactCardPadding)
                    .padding(.vertical, laughTrack.browseDensity.compactCardPadding)
                    .background(
                        RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                            .fill(laughTrack.colors.surfaceElevated)
                            .overlay(
                                RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                                    .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                            )
                    )
                }
            }
        }
        .detailSkeletonShimmer()
        .accessibilityLabel("Loading shows")
        .accessibilityAddTraits(.isImage)
    }
}

struct ComediansListSkeleton: View {
    var body: some View {
        EntityRowsSkeleton(
            label: "Loading comedians",
            artworkShape: .circle,
            showsDisclosureIndicator: false
        )
    }
}

struct ClubsListSkeleton: View {
    var body: some View {
        EntityRowsSkeleton(
            label: "Loading clubs",
            artworkShape: .circle,
            showsDisclosureIndicator: true
        )
    }
}

private struct EntityRowsSkeleton: View {
    @Environment(\.appTheme) private var theme

    let label: String
    let artworkShape: LaughTrackEntityRowArtworkShape
    let showsDisclosureIndicator: Bool

    var body: some View {
        entityRowsSkeleton
    }

    private var entityRowsSkeleton: some View {
        let laughTrack = theme.laughTrackTokens
        let block = laughTrack.colors.surfaceMuted

        return VStack(spacing: 10) {
            ForEach(0..<5, id: \.self) { _ in
                HStack(spacing: theme.spacing.md) {
                    artworkPlaceholder(block: block, shape: artworkShape)
                        .frame(width: 70, height: 70)

                    VStack(alignment: .leading, spacing: theme.spacing.xxs) {
                        RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 170, height: 16)
                        RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 132, height: 12)
                        RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 118, height: 12)
                    }

                    Spacer(minLength: 0)

                    if showsDisclosureIndicator {
                        RoundedRectangle(cornerRadius: 4)
                            .fill(block)
                            .frame(width: 8, height: 14)
                    }
                }
                .frame(maxWidth: .infinity, minHeight: 86, alignment: .leading)
                .padding(laughTrack.browseDensity.compactCardPadding)
                .background(
                    RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                        .fill(laughTrack.colors.surfaceElevated)
                        .overlay(
                            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                        )
                )
            }
        }
        .detailSkeletonShimmer()
        .accessibilityLabel(label)
        .accessibilityAddTraits(.isImage)
    }

    @ViewBuilder
    private func artworkPlaceholder(
        block: Color,
        shape: LaughTrackEntityRowArtworkShape
    ) -> some View {
        switch shape {
        case .circle:
            Circle().fill(block)
        case .roundedRectangle(let cornerRadius):
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous).fill(block)
        }
    }
}
