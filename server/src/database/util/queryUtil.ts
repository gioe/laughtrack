import { dbConnectionPool } from "../config.js"

export async function executeQuery<T>(queryString: string, 
    values?: any[]): Promise<T[]> {
    return dbConnectionPool.query(queryString, values)
    .then((response) => {
        const { rows } = response;
        return rows;
    })
}

export async function upsertAndReplace<T>(table: string, 
    inputs: string, 
    conflictingValue: string, 
    updateStatement: string, 
    values: any[]): Promise<T> {
    const queryString = `INSERT into ${table}${inputs} on conflict${conflictingValue} do update set ${updateStatement} RETURNING id`
    return executeQuery<T>(queryString, values)
    .then((queryResponse: any[]) => queryResponse[0])
}

export async function upsertAndDoNothing<T>(table: string, 
    inputs: string, 
    conflictingValue: string, 
    values: any[]): Promise<T> {
    const queryString = `INSERT into ${table}${inputs} on conflict${conflictingValue} do NOTHING RETURNING id`
    return executeQuery<T>(queryString, values)
    .then((queryResponse: any[]) => queryResponse[0])
}

export async function create<T>(table: string, 
    inputs: string, 
    values: any[]): Promise<T> {
    const queryString = `INSERT into ${table}${inputs} RETURNING id`
    return executeQuery<T>(queryString, values)
    .then((queryResponse: any[]) => queryResponse[0])
}

export async function getAll<T>(table: string): Promise<T[]> {
    const queryString = `SELECT * FROM ${table}`
    return executeQuery(queryString)
}

export async function getAllWithCondition<T>(table: string, 
    condition: string, 
    values?: any[]): Promise<T[]> {
    const queryString = `SELECT * FROM ${table} WHERE ${condition}`
    return executeQuery<T>(queryString, values)
}

export async function getFirstWithCondition<T>(table: string, 
    condition: string, 
    values?: any[]): Promise<T> {
        const queryString = `SELECT * FROM ${table} WHERE ${condition}`
    return executeQuery<T>(queryString, values)
    .then((queryResponse: any[]) => queryResponse[0])
}

export const deleteWithCondition = async (table: string, 
    clause?: string,
    values?: any[]): Promise<boolean> => {
    const queryString = `DELETE FROM ${table} WHERE ${clause}`
    return executeQuery<boolean>(queryString, values)
    .then((queryResponse: any[]) => queryResponse[0])
}

export async function checkForExistence(table: string, 
    clause?: string, 
    values?: any[]): Promise<boolean> {
    const queryString = `SELECT 1 FROM ${table} WHERE ${clause}`
    return executeQuery<boolean>(queryString, values)
    .then((queryResponse: any[]) => queryResponse[0])
}