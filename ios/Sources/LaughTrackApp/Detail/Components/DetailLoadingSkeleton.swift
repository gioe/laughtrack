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
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let block = laughTrack.colors.surfaceMuted

        VStack(alignment: .leading, spacing: 0) {
            Rectangle()
                .fill(block)
                .frame(height: 240)
                .clipped()
                .ignoresSafeArea(.container, edges: .top)

            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 10) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(block)
                        .frame(width: 170, height: 22)
                    HStack(spacing: 8) {
                        ForEach(0..<6, id: \.self) { _ in
                            RoundedRectangle(cornerRadius: 12)
                                .fill(block)
                                .frame(width: 44, height: 64)
                        }
                    }
                }

                VStack(spacing: 10) {
                    ForEach(0..<4, id: \.self) { _ in
                        RoundedRectangle(cornerRadius: laughTrack.radius.card)
                            .fill(block)
                            .frame(height: 62)
                    }
                }
            }
            .padding(.horizontal, theme.spacing.lg * 2)
            .padding(.vertical, theme.spacing.lg)

            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .detailSkeletonShimmer()
        .accessibilityLabel("Loading")
        .accessibilityAddTraits(.isImage)
    }
}

struct ShowDetailSkeleton: View {
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let block = laughTrack.colors.surfaceMuted

        VStack(alignment: .leading, spacing: 0) {
            Rectangle()
                .fill(block)
                .frame(height: 200)
                .clipped()
                .ignoresSafeArea(.container, edges: .top)

            VStack(alignment: .leading, spacing: 20) {
                VStack(spacing: 12) {
                    ForEach(0..<3, id: \.self) { _ in
                        HStack(spacing: 14) {
                            Circle().fill(block).frame(width: 36, height: 36)
                            VStack(alignment: .leading, spacing: 6) {
                                RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 60, height: 10)
                                RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 160, height: 14)
                            }
                            Spacer(minLength: 0)
                        }
                    }
                }
                .padding(theme.spacing.md)
                .background(
                    RoundedRectangle(cornerRadius: laughTrack.radius.card)
                        .fill(laughTrack.colors.surfaceElevated)
                        .overlay(
                            RoundedRectangle(cornerRadius: laughTrack.radius.card)
                                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                        )
                )

                VStack(alignment: .leading, spacing: 10) {
                    RoundedRectangle(cornerRadius: 4).fill(block).frame(width: 90, height: 22)
                    ForEach(0..<2, id: \.self) { _ in
                        RoundedRectangle(cornerRadius: laughTrack.radius.card)
                            .fill(block)
                            .frame(height: 56)
                    }
                }
            }
            .padding(.horizontal, theme.spacing.lg * 2)
            .padding(.vertical, theme.spacing.lg)

            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .detailSkeletonShimmer()
        .accessibilityLabel("Loading")
        .accessibilityAddTraits(.isImage)
    }
}
