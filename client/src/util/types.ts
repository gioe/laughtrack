import { ReactNode } from 'react'

export type BaseComponent = {
  children?: ReactNode
  className?: string
}


export type User = {

}

export type Comedian = {
  shows: Show[];
}

export type Show = {
  club: Club;
  dateTime: string;
  timeZone: string;
  name: string;
  ticketLink: string;
}

export type Club = {
  name: string;
  website: string;
}
