import { removeBadWhiteSpace } from "../util/stringUtil.js";
import { Show } from "./Show.js";

export class Comedian {
  name: string = ""
  shows: Show[] = []

  addShow(show: Show) {
    this.shows.push(show)
  }

  constructor(name: string) {
    this.name = this.formattedComedianName(name);
  }

  formattedComedianName = (name: string): string => {
    return removeBadWhiteSpace(name);
  }
  
}