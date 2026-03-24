import { EntityType } from "../../enum";
import { Entity } from "../../interface";
import { Comedian } from "../comedian/Comedian";
import { ComedianLineupDTO } from "../comedian/comedianLineup.interface";
import { ShowDTO, ShowInterface } from "./show.interface";
import { Ticket } from "../ticket/Ticket";
import { SocialData } from "../socialData/SocialData";
import { TicketDTO } from "../ticket/ticket.interface";

export class Show implements ShowInterface {
    // Properties
    name: string;
    date: Date;
    socialData?: SocialData;
    popularityScore?: number | undefined;
    clubName?: string | undefined;
    address?: string | undefined;
    tickets: Ticket[];
    id: number;
    type: EntityType = EntityType.Show;
    containedEntities: Entity[];
    lineup: Comedian[];
    isFavorite: boolean;
    lastScrapedDate?: Date;
    description?: string;
    room?: string | null;
    imageUrl: string;
    soldOut?: boolean;

    // Constructor
    constructor(input: ShowDTO) {
        this.name = input.name ?? "";
        this.date = input.date;
        this.socialData =
            input.social_data !== undefined
                ? new SocialData(input.social_data)
                : undefined;
        const lineupComedians = input.lineup
            ? input.lineup.map((item: ComedianLineupDTO) => new Comedian(item))
            : [];
        this.containedEntities = lineupComedians;
        this.lineup = lineupComedians;
        this.clubName = input.clubName;
        this.tickets = input.tickets
            ? input.tickets.map((item: TicketDTO) => new Ticket(item))
            : [];
        this.id = input.id ?? 0;
        this.description = input.description;
        this.room = input.room;
        this.address = input.address;
        this.imageUrl = input.imageUrl;
        this.soldOut = input.soldOut;
        this.isFavorite = false;
    }
    clubAddress?: string | undefined;
}
