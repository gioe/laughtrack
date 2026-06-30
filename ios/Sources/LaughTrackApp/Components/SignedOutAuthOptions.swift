import SwiftUI
import LaughTrackCore

struct SignedOutAuthOption: Identifiable, Equatable, Sendable {
    let provider: AuthProvider
    let title: String
    let symbolName: String

    var id: AuthProvider { provider }

    static let all: [SignedOutAuthOption] = AuthProvider.allCases.map {
        SignedOutAuthOption(
            provider: $0,
            title: $0.title,
            symbolName: $0.symbolName
        )
    }
}

struct SignedOutAuthOptionButton: View {
    @Environment(\.appTheme) private var theme

    let option: SignedOutAuthOption
    let action: (AuthProvider) -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button {
            action(option.provider)
        } label: {
            HStack(spacing: theme.spacing.sm) {
                Image(systemName: option.symbolName)
                    .font(.system(size: theme.iconSizes.md, weight: .semibold))
                    .frame(width: 24)

                Text(option.title)
                    .font(.system(size: 16, weight: .medium))
                    .lineLimit(1)
                    .minimumScaleFactor(0.86)
            }
            .foregroundStyle(option.provider == .apple ? laughTrack.colors.textInverse : laughTrack.colors.textPrimary)
            .frame(maxWidth: .infinity, minHeight: 50)
            .padding(.horizontal, theme.spacing.md)
            .contentShape(Rectangle())
            .background(buttonBackground)
            .overlay(buttonBorder)
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityLabel(option.title)
    }

    @ViewBuilder
    private var buttonBackground: some View {
        let laughTrack = theme.laughTrackTokens

        switch option.provider {
        case .apple:
            laughTrack.colors.textPrimary
        case .google, .email:
            laughTrack.colors.surfaceElevated
        }
    }

    private var buttonBorder: some View {
        let laughTrack = theme.laughTrackTokens

        return RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous)
            .stroke(option.provider == .apple ? .clear : laughTrack.colors.borderStrong.opacity(0.5), lineWidth: 1)
    }
}

#if DEBUG
struct DebugTestAuthButton: View {
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme
    @State private var isSigningIn = false
    @State private var errorMessage: String?

    private let config = DebugTestAuthConfiguration.resolve()

    var body: some View {
        if let config {
            VStack(spacing: theme.spacing.xs) {
                Button {
                    Task {
                        await signIn(config: config)
                    }
                } label: {
                    HStack(spacing: theme.spacing.sm) {
                        Image(systemName: isSigningIn ? "hourglass" : "wrench.and.screwdriver.fill")
                            .font(.system(size: theme.iconSizes.md, weight: .semibold))
                            .frame(width: 24)

                        Text(isSigningIn ? "Signing in..." : "Use test account")
                            .font(.system(size: 16, weight: .medium))
                            .lineLimit(1)
                            .minimumScaleFactor(0.86)
                    }
                    .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                    .frame(maxWidth: .infinity, minHeight: 50)
                    .padding(.horizontal, theme.spacing.md)
                    .contentShape(Rectangle())
                    .background(theme.laughTrackTokens.colors.surfaceElevated)
                    .overlay(
                        RoundedRectangle(cornerRadius: theme.laughTrackTokens.radius.pill, style: .continuous)
                            .stroke(theme.laughTrackTokens.colors.accentStrong.opacity(0.55), lineWidth: 1)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: theme.laughTrackTokens.radius.pill, style: .continuous))
                }
                .buttonStyle(.plain)
                .disabled(isSigningIn)
                .accessibilityLabel("Use test account")

                if let errorMessage {
                    Text(errorMessage)
                        .font(theme.laughTrackTokens.typography.metadata)
                        .foregroundStyle(theme.laughTrackTokens.colors.danger)
                        .multilineTextAlignment(.center)
                }
            }
        }
    }

    private func signIn(config: DebugTestAuthConfiguration) async {
        isSigningIn = true
        errorMessage = nil
        defer { isSigningIn = false }

        do {
            let response = try await fetchTokens(config: config)
            await authManager.signInWithTestTokens(
                accessToken: response.accessToken,
                refreshToken: response.refreshToken
            )
        } catch {
            errorMessage = "Test sign-in failed. Check the API URL and secret."
        }
    }

    private func fetchTokens(config: DebugTestAuthConfiguration) async throws -> TestAuthTokenResponse {
        var request = URLRequest(url: config.endpointURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(config.secret, forHTTPHeaderField: "X-Test-Auth-Secret")
        request.httpBody = try JSONEncoder().encode(TestAuthTokenRequest(email: config.email))

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse,
              (200..<300).contains(httpResponse.statusCode)
        else {
            throw URLError(.userAuthenticationRequired)
        }
        return try JSONDecoder().decode(TestAuthTokenResponse.self, from: data)
    }
}

private struct TestAuthTokenRequest: Encodable {
    let email: String
}

private struct TestAuthTokenResponse: Decodable {
    let accessToken: String
    let refreshToken: String
}
#endif
