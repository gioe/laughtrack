import { ReactNode } from 'react'

export type BaseComponent = {
  children?: ReactNode
  className?: string
}


export type User = {

}

export type Comedian = {
  name: string;
  image: string;
  shows: Show[];
  showCount: number;
}

export type Show = {
  clubName: string;
  clubWebsite: string;
  dateTime: Date;
  timeZone: string;
  name: string;
  ticketLink: string;
}



export type Club = {
  name: string;
  website: string;
}
