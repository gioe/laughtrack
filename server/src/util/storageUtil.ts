

import { Storage } from '@google-cloud/storage';
import fs from 'fs/promises';
import path from 'path';

const storage = new Storage();

export const downloadFile = async (bucketName: any, fileName: any) => {
    const __dirname = path.resolve();
    const cwd = path.join(__dirname, '..');
    const destination = path.join(cwd, fileName);

    const options = {
        destination,
    };
    

    await storage.bucket(bucketName).file(fileName).download(options);

    return readFile(destination)
}

export const readFile = async (sourceFile: string): Promise<string> => {
    return fs.readFile(sourceFile, { encoding: 'utf8' })
    .then((data: string) => deleteFile(sourceFile, JSON.parse(data)))
};

export const deleteFile = async (sourceFile: string, data: string): Promise<string> => {
    return fs.unlink(sourceFile)
    .then(() => data)
};