import { ShowHTMLConfiguration } from "../types/htmlconfigurable.interface.js";
import TimeContainerInterface from "../types/timeContainer.interface.js";
import { normalizeTimeString } from "../util/types/timeUtil.js";

export class TimeContainer implements TimeContainerInterface {

  config: ShowHTMLConfiguration;
  timeString: string = "";
  timeComponents: string[];

  constructor(timeString: string,
    config: ShowHTMLConfiguration) {
    this.config = config;
    this.timeString = normalizeTimeString(timeString, config);
    this.timeComponents = this.timeString.split(":")
  }

  getHour = (): number => {
    return Number(this.timeComponents[0]);
  }

  getMinute = (): number => {
    return Number(this.timeComponents[1]);
  }

  getSeconds = (): number => {
    return 0;
  }

}