'use server';
import { scrapeClubs } from "../../../../../../jobs/scrape/club";
import { ClubDTO } from "../../../../../../objects/class/club/club.interface";
import { getDB } from "../../.././../../../database";
const { database } = getDB();

export async function scrape(id: number) {
    console.log(`Scraping ${id}`)
    return database.queries.getClubById(id)
        .then((value: ClubDTO | null) => {
            if (value) return scrapeClubs([value], false)
            throw new Error(`No value returned`)
        })
        .catch((error: Error) => {
            console.log(error)
            throw new Error(error.message)
        })
}

export async function clear(id: number) {
    console.log(`Clear club id ${id}`)
    return database.actions.deleteShowsForClub(id)
        .catch((error: Error) => {
            console.log(error)
            throw new Error(error.message)
        })
}
