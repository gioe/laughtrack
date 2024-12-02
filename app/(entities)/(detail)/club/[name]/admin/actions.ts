'use server';
import { getDB } from "../../.././../../../database";
const { database } = getDB();
import axios from "axios";

export async function scrape(id: number) {
    return axios
        .post(`/api/club/${id}/scrape`)
}

export async function clear(id: number) {
    database.actions.deleteShowsForClub(id)
        .catch((error: Error) => {
            console.log(error)
            throw new Error(error.message)
        })
}
