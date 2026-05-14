import { EntityResponseDTO } from "@/objects/interface/paginatedEntity.interface";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { ComedianPodcastAppearanceDTO } from "@/objects/class/comedian/podcastAppearance.interface";
import { RoomHistoryDTO } from "@/objects/class/comedian/roomHistory.interface";

export interface ComedianDetailResponse extends EntityResponseDTO<ComedianDTO> {
    relatedComedians: ComedianDTO[];
    roomHistory: RoomHistoryDTO[];
    podcastAppearances: ComedianPodcastAppearanceDTO[];
}
