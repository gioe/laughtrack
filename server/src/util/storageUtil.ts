

import { Storage, GetFilesResponse, File, TransferManager, Bucket, DownloadResponse } from '@google-cloud/storage';

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