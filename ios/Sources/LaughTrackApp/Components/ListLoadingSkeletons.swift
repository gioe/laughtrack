import SwiftUI

struct ShowsListSkeleton: View {
    @Environment(\.appTheme) private var theme

    var includesHero: Bool = false
    var rowCount: Int = 5

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let block = laughTrack.colors.surfaceMuted

        VStack(spacing: 12) {
            if includesHero {
                RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                    .fill(block)
                    .frame(height: 280)
            }

            VStack(spacing: 10) {
                ForEach(0..<rowCount, id: \.self) { _ in
                    HStack(spacing: 12) {
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .fill(block)
                            .frame(width: 56, height: 56)
                        VStack(alignment: .leading, spacing: 6) {
                            RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 180, height: 14)
                            RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 120, height: 12)
                            RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 80, height: 12)
                        }
                        Spacer(minLength: 0)
                    }
                    .padding(10)
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
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let block = laughTrack.colors.surfaceMuted

        VStack(spacing: 10) {
            ForEach(0..<5, id: \.self) { _ in
                HStack(spacing: 14) {
                    Circle()
                        .fill(block)
                        .frame(width: 60, height: 60)
                    VStack(alignment: .leading, spacing: 6) {
                        RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 160, height: 14)
                        RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 110, height: 12)
                    }
                    Spacer(minLength: 0)
                }
                .padding(10)
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
        .accessibilityLabel("Loading comedians")
        .accessibilityAddTraits(.isImage)
    }
}

struct ClubsListSkeleton: View {
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let block = laughTrack.colors.surfaceMuted

        VStack(spacing: 10) {
            ForEach(0..<5, id: \.self) { _ in
                HStack(spacing: 14) {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(block)
                        .frame(width: 56, height: 56)
                    VStack(alignment: .leading, spacing: 6) {
                        RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 180, height: 14)
                        RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 130, height: 12)
                    }
                    Spacer(minLength: 0)
                }
                .padding(10)
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
        .accessibilityLabel("Loading clubs")
        .accessibilityAddTraits(.isImage)
    }
}
