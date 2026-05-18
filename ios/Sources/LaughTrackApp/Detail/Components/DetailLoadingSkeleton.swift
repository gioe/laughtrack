import SwiftUI

private struct ShimmerModifier: ViewModifier {
    @State private var phase: CGFloat = -1.0

    func body(content: Content) -> some View {
        content
            .overlay(
                GeometryReader { proxy in
                    LinearGradient(
                        gradient: Gradient(stops: [
                            .init(color: .white.opacity(0), location: 0.0),
                            .init(color: .white.opacity(0.55), location: 0.5),
                            .init(color: .white.opacity(0), location: 1.0)
                        ]),
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                    .frame(width: proxy.size.width * 0.6)
                    .offset(x: phase * proxy.size.width * 1.6)
                    .blendMode(.plusLighter)
                }
            )
            .mask(content)
            .onAppear {
                withAnimation(.linear(duration: 1.4).repeatForever(autoreverses: false)) {
                    phase = 1.0
                }
            }
    }
}

extension View {
    func detailSkeletonShimmer() -> some View {
        modifier(ShimmerModifier())
    }
}

struct CalendarDetailSkeleton: View {
    var body: some View {
        DetailHeroContentSkeleton(kind: .calendar)
    }
}

struct ShowDetailSkeleton: View {
    var body: some View {
        DetailHeroContentSkeleton(kind: .show)
    }
}

private enum DetailSkeletonKind {
    case calendar
    case show
}

private struct DetailHeroContentSkeleton: View {
    @Environment(\.appTheme) private var theme

    let kind: DetailSkeletonKind

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let block = laughTrack.colors.surfaceMuted

        VStack(alignment: .leading, spacing: 0) {
            ZStack(alignment: .bottomLeading) {
                Rectangle()
                    .fill(block)

                LinearGradient(
                    stops: [
                        .init(color: laughTrack.colors.heroStart.opacity(0.10), location: 0.0),
                        .init(color: laughTrack.colors.heroStart.opacity(0.42), location: 0.46),
                        .init(color: laughTrack.colors.heroStart.opacity(0.94), location: 1.0)
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                )

                VStack(alignment: .leading, spacing: 10) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(block)
                        .frame(width: 120, height: 14)
                    RoundedRectangle(cornerRadius: 8)
                        .fill(block)
                        .frame(width: 260, height: 34)

                    if kind == .calendar {
                        HStack(spacing: theme.spacing.md) {
                            ForEach(0..<2, id: \.self) { _ in
                                VStack(spacing: 3) {
                                    Circle()
                                        .fill(block)
                                        .frame(width: 40, height: 40)
                                    RoundedRectangle(cornerRadius: 4)
                                        .fill(block)
                                        .frame(width: 44, height: 10)
                                }
                            }
                        }
                    } else {
                        RoundedRectangle(cornerRadius: 12)
                            .fill(block)
                            .frame(width: 84, height: 24)
                    }
                }
                .padding(laughTrack.spacing.heroPadding)
            }
            .frame(height: DetailHeroLayout.maximumMediaHeight)
            .clipped()
            .ignoresSafeArea(.container, edges: .top)

            VStack(alignment: .leading, spacing: 20) {
                if kind == .calendar {
                    RoundedRectangle(cornerRadius: laughTrack.radius.card)
                        .fill(block)
                        .frame(height: 72)
                }

                VStack(spacing: 0) {
                    ForEach(0..<4, id: \.self) { index in
                        HStack(spacing: theme.spacing.sm) {
                            RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 74, height: 11)
                            RoundedRectangle(cornerRadius: 4).fill(block).frame(width: index == 0 ? 170 : 130, height: 15)
                            Spacer(minLength: 0)
                            RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 18, height: 18)
                        }
                        .padding(.vertical, theme.spacing.sm)

                        if index < 3 {
                            Rectangle()
                                .fill(laughTrack.colors.borderSubtle)
                                .frame(height: 1)
                        }
                    }
                }
                .padding(.horizontal, theme.spacing.md)
                .background(
                    RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                        .fill(laughTrack.colors.surfaceElevated)
                        .overlay(
                            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                        )
                )

                VStack(alignment: .leading, spacing: 10) {
                    RoundedRectangle(cornerRadius: 4).fill(block).frame(width: kind == .show ? 90 : 150, height: 22)
                    ForEach(0..<3, id: \.self) { _ in
                        HStack(spacing: theme.spacing.md) {
                            Circle().fill(block).frame(width: 44, height: 44)
                            VStack(alignment: .leading, spacing: 6) {
                                RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 160, height: 14)
                                RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 112, height: 12)
                            }
                            Spacer(minLength: 0)
                        }
                        .padding(theme.spacing.sm)
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
            .padding(.horizontal, 8)
            .padding(.vertical, theme.spacing.lg)

            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .detailSkeletonShimmer()
        .accessibilityLabel("Loading")
        .accessibilityAddTraits(.isImage)
    }
}
