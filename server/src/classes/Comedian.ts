import { FieldValue } from "@google-cloud/firestore";
import { ComedianInterface } from "../types/comedian.interface.js";
import { removeAllWhiteSpace, removeBadWhiteSpace } from "../util/types/stringUtil.js";
import { Show } from "./Show.js";

export class Comedian implements ComedianInterface {
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
  
  getDocumentName = () => { return removeAllWhiteSpace(this.name).toLowerCase(); }

  getData = () => {
    return {
      name: this.name,
      shows: FieldValue.arrayUnion(...this.shows),
    }
  }

}