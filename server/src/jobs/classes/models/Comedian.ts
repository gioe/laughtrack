import { ComedianInterface } from "../../../common/interfaces/comedian.interface.js";
import { removeBadWhiteSpace } from "../../util/stringUtil.js";

export class Comedian implements ComedianInterface {
  
  name: string;

  constructor(name: string) {
    this.name = removeBadWhiteSpace(name);
  }

}