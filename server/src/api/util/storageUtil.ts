import { isLocal } from './environmentUtil.js';
import { readFileFromFileSystem } from '../../common/util/fileSystemUtil.js';
import { readFileFromBucket } from './cloudStorageUtil.js';

export async function readFile(fileName: string): Promise<string> {
    if (isLocal) {
        return readFileFromFileSystem(fileName)
    } else {
        return readFileFromBucket(fileName)
    }
}