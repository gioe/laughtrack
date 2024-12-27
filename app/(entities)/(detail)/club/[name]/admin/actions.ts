'use server';
import { getDB } from "../../.././../../../database";
const { database } = getDB();

export async function clear(id: number) {
    console.log(`Clear club id ${id}`)
    return database.actions.deleteShowsForClub(id)
        .catch((error: Error) => {
            console.log(error)
            throw new Error(error.message)
        })
}
