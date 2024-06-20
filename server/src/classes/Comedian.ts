import { FieldValue } from "@google-cloud/firestore";
import { ComedianInterface } from "../types/comedian.interface.js";
import { Show } from "../types/show.interface.js";
import { removeWhiteSpace } from "../util/string/stringUtil.js";

export class Comedian implements ComedianInterface {
  name: string = ""
  website: string = ""
  shows: Show[] = []

  addShows(shows: Show[]) {
    shows.forEach(show => {
      this.shows.push(show)
    })
  }

  constructor(name: string, website: string) {
    this.name = name
    if (website === undefined) {
      this.website = "";
    } else {
      this.website = website;
    }
  }

  getDocumentName = () => {
    return removeWhiteSpace(this.name);
  }

  getData = () => {
    return {
      name: this.name,
      website: this.website,
      shows: FieldValue.arrayUnion(...this.shows),
    }
  }

}