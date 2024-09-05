import fs from 'fs';

export const readFile = (sourceFile: string) => {
    try {
        const data = fs.readFileSync(sourceFile, 'utf8');
        return JSON.parse(data);
    } catch (err) {
        console.error('Error reading file:', err);
    }
};

export const deleteFile = (sourceFile: string) => {
    fs.unlink(sourceFile, (err) => {
        if (err) throw err;
    })
};