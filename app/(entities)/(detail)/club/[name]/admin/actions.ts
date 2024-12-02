'use server';

import axios from "axios";

export async function scrape(id: number) {
    return axios
        .post(`/api/club/${id}/scrape`)
}

export async function clear(id: number) {
    console.log(`Clearing ${id}`)
    return axios
        .post(`/api/${id}/clear`)
}
