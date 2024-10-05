
export class TimeContainer {

  timeString: string = "";
  timeComponents: string[];

  constructor(timeString: string) {
    this.timeString = timeString;
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