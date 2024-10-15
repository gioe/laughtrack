import { getMeridiemByRegex, getTimeByRegex } from "../../../common/util/timeUtil.js";

export class TimeContainer {

  timeComponents: string[];
  timeString: string;

  constructor(inputString: string) {

    var timeValue = getTimeByRegex(inputString);
    this.timeString = timeValue

    var meridiem = getMeridiemByRegex(inputString);

    var [hours, minutes] = timeValue.split(':');

    if (parseInt(hours) == 12) {
        hours = "00"
    }
    
    const adjustedHours = parseInt(hours) + (meridiem == 'PM' ? 12 : 0);
    const timeString = minutes === undefined ? `${adjustedHours}:00` : `${adjustedHours}:${minutes}`;
    this.timeComponents = timeString.split(":")
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

  getTimeString = (): string => {
    return this.timeString;
  }

}