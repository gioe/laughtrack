import { EntityType } from "../../enum";
import { Entity } from "../../interface";
import { Comedian } from "../comedian/Comedian";
import { ComedianDTO } from "../comedian/comedian.interface";
import { ShowDTO, ShowInterface } from "./show.interface";
import { Ticket } from "../ticket/Ticket";
import { SocialData } from "../socialData/SocialData";

export class Show implements ShowInterface {
    // Properties
    name: string;
    date: Date;
    socialData?: SocialData;
    popularityScore?: number | undefined;
    clubName?: string | undefined;
    address?: string | undefined;
    ticket: Ticket;
    tagIds: number[];
    id: number;
    type: EntityType = EntityType.Show;
    containedEntities: Entity[]
    lineup: Comedian[]
    isFavorite: boolean;
    lastScrapedDate?: Date;
    description?: string;
    imageUrl: string;
    soldOut?: boolean

    // Constructor
    constructor(input: ShowDTO) {
        this.name = input.name ?? "";
        this.date = input.date;
        this.socialData = input.social_data !== undefined ? new SocialData(input.social_data) : undefined;
        this.containedEntities = input.lineup ? input.lineup.map((item: ComedianDTO) => new Comedian(item)) : []
        this.lineup = input.lineup ? input.lineup.map((item: ComedianDTO) => new Comedian(item)) : []
        this.clubName = input.clubName;
        this.ticket = new Ticket(input.ticket)
        this.tagIds = input.tags ? input.tags : [];
        this.id = input.id ?? 0
        this.description = input.description
        this.address = input.address
        this.imageUrl = input.imageUrl
        this.soldOut = input.soldOut
    }

}
