import Foundation

/// Entity kind rendered when artwork is missing or fails to load, mirroring the
/// Android RemoteImageFallback enum (TASK-3716) and the icon vocabulary the home
/// rails, search surfaces, and detail heroes already use. Pick the kind matching
/// what the image depicts; `.generic` is the default for surfaces with no single
/// entity. This is the single source of truth for the entity fallback SF Symbol
/// names — artwork-fallback surfaces must resolve icons through it rather than
/// hard-coding the literals.
enum ArtworkFallbackKind {
    case comedian
    case club
    case show
    case podcast
    case person
    case generic

    var systemImage: String {
        switch self {
        case .comedian: return "music.mic"
        case .club: return "building.2.fill"
        case .show: return "ticket.fill"
        case .podcast: return "headphones"
        case .person: return "person.fill"
        case .generic: return "photo"
        }
    }
}
