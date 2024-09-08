

import { Storage, GetFilesResponse, File, TransferManager, Bucket, DownloadResponse } from '@google-cloud/storage';
import fs from 'fs/promises';
import path from 'path';
import { runTasks } from './promiseUtil.js';

const storage = new Storage()

export async function downloadBucketContents(bucketString: string): Promise<void> {

    const bucket = storage.bucket(bucketString);
    bucket.setUserProject(process.env.CLOUD_STORAGE_PROJECT_ID as string);

    const transferManager = new TransferManager(bucket);

    transferManager.downloadManyFiles(process.env.CLOUD_STORAGE_FOLDER_NAME as string, {
        passthroughOptions: {
            destination: process.env.DIRECTORY_PATH as string
        }
    })
    .catch((error: Error) => console.log(error))
}

export const readFile = async (sourceFile: string): Promise<string> => {
    const filePath = getPath(sourceFile)
    return fs.readFile(filePath, { encoding: 'utf8' })
    .then((data: string) => JSON.parse(data))
    .catch((error: Error) => console.log(error))
};

const getPath = (fileName: string) => {
    return path.join(process.env.DIRECTORY_PATH as string, fileName);
}