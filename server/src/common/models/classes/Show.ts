
import { Comedian } from "./Comedian.js";
import { CreateShowDTO, ShowInput } from "../interfaces/show.interface.js";
import { CreateComedianDTO } from "../interfaces/comedian.interface.js";

export class Show {

  lineup: Comedian[];
  dateTime: Date;
  ticketLink: string;
  name: string;

  clubId: number = 0;

  constructor(showInput: ShowInput) {
    this.lineup = showInput.lineup
    this.dateTime = showInput.dateTime;
    this.ticketLink = showInput.ticketLink;
    this.name = showInput.name
  }

  setClubId = (id: number) => {
    this.clubId = id;
  }

  asCreateShowDTO = (): CreateShowDTO => {
    return {
      club_id: this.clubId,
      date_time: this.dateTime,
      ticket_link: this.ticketLink,
      name: this.name 
    }
  }

  asCreateComedianDTOArray = (): CreateComedianDTO[] => {
    return this.lineup.map((comedian: Comedian) => comedian.asCreateComedianDTO())
  }
 
}