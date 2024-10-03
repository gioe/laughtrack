import { ComedianInterface } from "../../../common/interfaces/comedian.interface.js";
import { removeBadWhiteSpace } from "../../util/stringUtil.js";

export class Comedian implements ComedianInterface {
  
  instagramFollowers = 0;
  nonComedian: boolean = false;
  tiktokFollowers = 0;
  isPseudonym = false;
  id: number = 0;
  name: string;
  poplarityScore: number = 0;

  constructor(name: string) {
    this.name = removeBadWhiteSpace(name);
  }


}