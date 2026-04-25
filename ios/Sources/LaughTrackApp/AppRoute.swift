enum AppRoute: Hashable, Codable {
    case home
    case search
    case library
    case profile
    case settings
    case showDetail(Int)
    case comedianDetail(Int)
    case clubDetail(Int)
}
