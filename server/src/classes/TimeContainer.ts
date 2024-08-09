import TimeContainerInterface from "../types/timeContainer.interface.js";
import { normalizeTimeString } from "../util/types/timeUtil.js";
import { ScrapingConfig } from "./ScrapingConfig.js";

export class TimeContainer implements TimeContainerInterface {

  timeString: string = "";
  timeComponents: string[];

  constructor(timeString: string,
    config: ScrapingConfig) {
    this.timeString = normalizeTimeString(timeString, config);
    this.timeComponents = this.timeString.split(":")
  }

  getHours = (): number => {
    return Number(this.timeComponents[0]);
  }

  getMinutes = (): number => {
    return Number(this.timeComponents[1]);
  }

  getSeconds = (): number => {
    return 0;
  }

}