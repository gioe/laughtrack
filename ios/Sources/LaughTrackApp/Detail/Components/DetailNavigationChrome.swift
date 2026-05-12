import SwiftUI

enum DetailNavigationChrome {
    enum Entity {
        case club
        case comedian
        case show
    }

    static let extendsHeroBehindTopSafeArea = true

    static func title(for entity: Entity) -> String {
        switch entity {
        case .club:
            return "Club"
        case .comedian:
            return "Comedian"
        case .show:
            return "Show"
        }
    }
}

struct EntityDetailNavigationChrome: ViewModifier {
    @Environment(\.appTheme) private var theme
    @Environment(\.dismiss) private var dismiss

    let entity: DetailNavigationChrome.Entity

    func body(content: Content) -> some View {
        #if os(iOS)
        content
            .navigationBarBackButtonHidden(true)
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "chevron.left")
                            .font(.system(size: theme.iconSizes.sm, weight: .bold))
                            .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                            .frame(width: 36, height: 36)
                            .background(.ultraThinMaterial, in: Circle())
                            .overlay(
                                Circle()
                                    .stroke(theme.laughTrackTokens.colors.borderSubtle, lineWidth: 1)
                            )
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Back")
                }

                ToolbarItem(placement: .principal) {
                    Text(DetailNavigationChrome.title(for: entity))
                        .font(theme.laughTrackTokens.typography.cardTitle)
                        .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                        .lineLimit(2)
                        .multilineTextAlignment(.center)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        #else
        content
            .navigationTitle(DetailNavigationChrome.title(for: entity))
        #endif
    }
}
