

import { Storage } from '@google-cloud/storage';
import fs from 'fs/promises';
import path from 'path';

const storage = new Storage();

export async function downloadFile(fileName: any): Promise<void> {
    const __dirname = path.resolve();
    const cwd = path.join(__dirname, '..');
    const destination = path.join(cwd, fileName);

    const options = {
        destination,
    };

    storage.bucket(process.env.STORAGE_BUCKET as string).file(fileName).download(options)
    .catch((error) => {
        console.error(error)
    })

}

export const readFile = async (sourceFile: string): Promise<string> => {
    return fs.readFile(sourceFile, { encoding: 'utf8' })
    .then((data: string) => deleteFile(sourceFile, JSON.parse(data)))
};

export const deleteFile = async (sourceFile: string, data: string): Promise<string> => {
    return fs.unlink(sourceFile)
    .then(() => data)
};