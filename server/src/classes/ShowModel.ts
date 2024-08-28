import { Club } from "../api/interfaces/club.interface.js";
import { Comedian } from "../api/interfaces/comedian.interface.js";
import { Show } from "../api/interfaces/show.interface.js";
import { ComedianModel } from "./ComedianModel.js";

export class ShowModel implements Show {

  dateTime: Date;
  ticketLink: string;
  comedians: Comedian[]
  club?: Club

  constructor(scrapedValues: string[], comedians: ComedianModel[]) {
    console.log(scrapedValues)
    this.comedians = comedians
    this.dateTime = new Date()
    this.ticketLink = ""
  }

  setClub = (club: Club) => {
    this.club = club
  }

}