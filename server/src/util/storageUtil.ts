

import { Storage } from '@google-cloud/storage';
import fs from 'fs/promises';
import path from 'path';

export const downloadFile = async (bucketName: any, fileName: any, destFileName: string) => {
    const __dirname = path.resolve();
    const cwd = path.join(__dirname, '..');
    const destination = path.join(cwd, destFileName);

    const storage = new Storage();
    const options = {
        destination,
    };
    
    await storage.bucket(bucketName).file(fileName).download(options);

    return readFile(destFileName)
}

export const readFile = async (sourceFile: string): Promise<string> => {
    return fs.readFile(sourceFile, { encoding: 'utf8' })
    .then((data: string) => JSON.parse(data))
    .catch((err) => {
        console.error('Error reading file:', err);
    })
};

export const deleteFile = async (sourceFile: string) => {
    return fs.unlink(sourceFile)
    .catch((err) => {
        console.error('Error deleting file:', err);
    })
};