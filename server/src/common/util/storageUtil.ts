import * as fsPromises from 'fs/promises';
import * as fsSync from 'fs';
import path from 'path';
import { isLocal } from './environmentUtil.js';
import { Storage, TransferManager, DownloadResponse } from '@google-cloud/storage';

const storage = new Storage()
const bucket = storage.bucket(process.env.STORAGE_BUCKET as string);
bucket.setUserProject(process.env.CLOUD_STORAGE_PROJECT_ID as string);


export async function readFile(fileName: string): Promise<string> {
    if (isLocal) {
        return readFileFromFileSystem(fileName)
    } else {
        return readFileFromBucket(fileName)
    }
}

export const readFileFromFileSystem = async (sourceFile: string): Promise<string> => {
    const filePath = getPath(sourceFile)
    return fsPromises.readFile(filePath, { encoding: 'utf8' })
    .then((data: string) => JSON.parse(data))
    .catch((error: Error) => console.log(error))
};

const getPath = (fileName: string) => {
    return path.join(process.env.DIRECTORY_PATH as string, fileName);
}

export const checkForFileExistence = (path: string) => {
    return fsSync.existsSync(path)
}

export const makeDirectory = (path: string) => {
    return fsSync.mkdirSync(path)
}

export const readFileFromBucket = async (sourceFile: string): Promise<string> => {
    return bucket.file(sourceFile).download()
    .then((response: DownloadResponse) => JSON.parse(response[0].toString('utf8')))
    .catch((error: Error) => console.log(error))
};


export async function downloadBucketContents(): Promise<void> {

    const transferManager = new TransferManager(bucket);

    transferManager.downloadManyFiles(process.env.CLOUD_STORAGE_FOLDER_NAME as string, {
        passthroughOptions: {
            destination: process.env.DIRECTORY_PATH as string
        }
    })
    .catch((error: Error) => console.log(error))

}