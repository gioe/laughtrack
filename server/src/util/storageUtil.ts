

import { Storage, GetFilesResponse, File } from '@google-cloud/storage';
import fs from 'fs/promises';
import path from 'path';

const storage = new Storage()
const bucket = storage.bucket(process.env.STORAGE_BUCKET as string);

export async function downloadFile(fileName: any): Promise<void> {
    const __dirname = path.resolve();
    const cwd = path.join(__dirname, '..');
    const destination = path.join(cwd, fileName);

    const options = {
        destination,
    };

    bucket.getFiles()
    .then((response: GetFilesResponse) => {
        return response[0].forEach((file: File) => console.log(file.name))
    })
    .catch((error) => console.log(error))

}

export const readFile = async (sourceFile: string): Promise<string> => {
    return fs.readFile(sourceFile, { encoding: 'utf8' })
    .then((data: string) => deleteFile(sourceFile, JSON.parse(data)))
};

export const deleteFile = async (sourceFile: string, data: string): Promise<string> => {
    return fs.unlink(sourceFile)
    .then(() => data)
};