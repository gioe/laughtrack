import pkg from 'pg';
const { Pool } = pkg;
import { AuthTypes, Connector, IpAddressTypes } from '@google-cloud/cloud-sql-connector';
    
export var dbConnectionPool: pkg.Pool;

export async function generateLocalDBConnection() {
  console.log("Building local DB connection")
  const connector = new Connector();

  const clientOpts = connector.getOptions({
    instanceConnectionName: process.env.INSTANCE_CONNECTION_NAME as string,
    authType: AuthTypes.IAM,
    ipType: IpAddressTypes.PUBLIC,
  });
  
  dbConnectionPool = new Pool({
    ...clientOpts,
    user: process.env.LOCAL_DB_USER as string,
    database: process.env.DB_NAME as string, 
    max: 5
  })

  await generateTables(dbConnectionPool)
}

export async function generateRemoteDBConnection () {
  console.log("Building remote DB connection")
  dbConnectionPool = new Pool({
    user: process.env.DB_USER as string,
    database: process.env.DB_NAME as string, 
    password: process.env.DB_PASSWORD as string,
    host: process.env.INSTANCE_UNIX_SOCKET as string,
    max: 5
  })

  await generateTables(dbConnectionPool)
}

async function generateTables(pool: pkg.Pool) {
  return createClubsTable(pool)
  .then(() => createShowsTable(pool))
  .then(() => createComediansTable(pool))
  .then(() => createShowComediansTable(pool))
  .then(() => createUsersTable(pool));
}


export async function createClubsTable(pool: pkg.Pool) {
  try {
    const query = `
      CREATE TABLE IF NOT EXISTS clubs (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL unique,
        base_url TEXT NOT NULL,
        schedule_page_url TEXT NOT NULL,
        timezone TEXT NOT NULL,
        scraping_config JSON NOT NULL
      );
    `;
    await pool.query(query);
  } catch (err) {
    console.error(err);
    console.error('Clubs table creation failed');
  }
}

export async function createShowsTable(pool: pkg.Pool) {
  try {
    const query = `
      CREATE TABLE IF NOT EXISTS shows (
        id SERIAL PRIMARY KEY,
        date_time TIMESTAMP NOT NULL,
        ticket_link TEXT NOT NULL,
        club_id INTEGER, 
        UNIQUE (club_id, date_time),
        CONSTRAINT fk_club FOREIGN KEY(club_id) REFERENCES clubs(id)
      );
    `;
    await pool.query(query);
  } catch (err) {
    console.error(err);
    console.error('Shows table creation failed');
  }
}

export async function createComediansTable(pool: pkg.Pool) {
  try {
    const query = `
      CREATE TABLE IF NOT EXISTS comedians (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL unique,
        instagram TEXT
      );
    `;

    await pool.query(query);
  } catch (err) {
    console.error(err);
    console.error('Comedians table creation failed');
  }
}

export async function createShowComediansTable(pool: pkg.Pool) {
  try {
    const query = `
      CREATE TABLE IF NOT EXISTS show_comedians (
      id SERIAL PRIMARY KEY,
      show_id INTEGER,
      comedian_id INTEGER,
      CONSTRAINT fk_shows FOREIGN KEY(show_id) REFERENCES shows(id),
      CONSTRAINT fk_comedians FOREIGN KEY(comedian_id) REFERENCES comedians(id)
      );
    `;

    await pool.query(query);
  } catch (err) {
    console.error(err);
    console.error('Show comedians table creation failed');
  }
}

export async function createUsersTable(pool: pkg.Pool) {
  try {
    const query = `
      CREATE TABLE IF NOT EXISTS users (
      id SERIAL PRIMARY KEY,
      email TEXT NOT NULL UNIQUE,
      password VARCHAR NOT NULL,
      role TEXT NOT NULL DEFAULT 'user'
      );
    `;

    await pool.query(query);
  } catch (err) {
    console.error(err);
    console.error('Users table creation failed');
  }
}
