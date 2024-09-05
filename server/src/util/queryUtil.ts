import pool from "../database/config.js"

export async function executeQuery<T>(queryString: string, values?: any[]): Promise<T[]> {
    var response;

    if (values !== undefined) {
        const { rows } = await pool.query(queryString, values)
        response = rows;
    } else {
        const { rows } = await pool.query(queryString)
        response = rows; 
    }

    return response
}

export async function upsert<T>(table: string, inputs: string, conflictingValue: string, updateStatement: string, values: any[]): Promise<T> {
    const queryString = `INSERT into ${table}${inputs} on conflict${conflictingValue} do update set ${updateStatement} RETURNING id`
    const { rows } = await pool.query(queryString, values)
    return rows[0];
}

export async function create<T>(table: string, inputs: string, values: any[]): Promise<T> {
    const queryString = `INSERT into ${table}${inputs} RETURNING id`
    const { rows } = await pool.query(queryString, values)
    return rows[0];
}

export async function getAll<T>(table: string): Promise<T[]> {
    const queryString = `SELECT * FROM ${table}`
    const { rows } = await pool.query(queryString)
    return rows
}

export async function getAllWithCondition<T>(table: string, 
    condition: string, 
    values?: any[]): Promise<T[]> {
    const queryString = `SELECT * FROM ${table} WHERE ${condition}`
    const { rows } = await pool.query(queryString, values)
    return rows
}

export async function getFirstWithCondition<T>(table: string, 
    condition: string, 
    values: any[]): Promise<T> {
    const queryString = `SELECT * FROM ${table} WHERE ${condition}`
    const { rows } = await pool.query(queryString, values)
    return rows[0]
}

export const deleteWithCondition = async (table: string, clause?: string, values?: any[]): Promise<boolean> => {
    const queryString = `DELETE FROM ${table} WHERE ${clause}`
    const { rows } = await pool.query(queryString, values)
    return rows[0]
}

export async function checkForExistence(table: string, clause?: string, values?: any[]): Promise<boolean> {
    const queryString = `SELECT 1 FROM ${table} WHERE ${clause}`
    const { rows } = await pool.query(queryString, values)
    return rows[0]
}

export async function updateTableById<T>(table: string, 
    updateString: string, 
    values: any[],
    condition?: string): Promise<T> {
        
    var response;
    
    if (condition !== undefined) {
        const { rows } = await pool.query(`UPDATE ${table} SET ${updateString} WHERE ${condition}`, [values])
        response = rows[0]
    } else {
        const { rows } = await pool.query(`UPDATE ${table} SET ${updateString}`, [values])
        response = rows[0]
    }

    return response;
}
