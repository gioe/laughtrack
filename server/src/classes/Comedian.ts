import { FieldValue } from "@google-cloud/firestore";
import { ComedianInterface } from "../types/comedian.interface.js";
import { Show } from "../types/show.interface.js";
import { removeAllWhiteSpace, removeBadWhiteSpace } from "../util/types/stringUtil.js";

export class Comedian implements ComedianInterface {
  name: string = ""
  website: string = ""
  shows: Show[] = []

  addShow(show: Show) {
    this.shows.push(show)
  }

  constructor(name: string, website: string) {
    this.name = this.formattedComedianName(name);
    this.website = website;
  }

  formattedComedianName = (name: string): string => {
    return removeBadWhiteSpace(name);
  }

  formattedComedianWebsite = (website: string): string => {
    return website
  }

  getDocumentName = () => { return removeAllWhiteSpace(this.name).toLowerCase(); }

  getData = () => {
    return {
      name: this.name,
      website: this.website,
      shows: FieldValue.arrayUnion(...this.shows),
    }
  }

}