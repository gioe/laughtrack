import { ScrapingConfig } from "../../../common/models/ScrapingConfig.js";
import { normalizeTimeString } from "../../../common/util/timeUtil.js";

export class TimeContainer {

  timeString: string = "";
  timeComponents: string[];

  constructor(timeString: string, config: ScrapingConfig) {
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