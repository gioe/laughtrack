import { FieldValue, Firestore } from "@google-cloud/firestore"
import { Show } from "../../types/show.interface.js";
import { removeWhiteSpace } from "../string/stringUtil.js";

const SHOW_COLLECTION = 'shows'

export const writeToFirestore = async (shows: Show[], storagePath: string) => {
  
  const db = new Firestore({
    projectId: process.env.GCP_PROJECT_ID,
    keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS_PATH,
  });
  
  const showsRef = db.collection(SHOW_COLLECTION)

  for (const show of shows) {
    for (const comedian of show.comedians) {
      const comedianDocTitle = removeWhiteSpace(comedian.name.toLowerCase());
     
      const showsRef = db.collection(SHOW_COLLECTION).doc(comedianDocTitle);
      
      showsRef.get().then((docSnapshot) => {
        if (docSnapshot.exists) {
          showsRef.update(
            {
            shows: FieldValue.arrayUnion({
              dateTime: show.dateTime,
              showName: show.name,
            })
          });
        } else {
          showsRef.set({
            lastUpdate: new Date().toISOString(),
            comedian: comedian.name, 
            shows: FieldValue.arrayUnion({
              dateTime: show.dateTime,
              showName: show.name,
            })
          });
        }
    });
    }
  }
}

export const getComedianShowDocuments = async (comedian: string) => {
  
  const db = new Firestore({
    projectId: process.env.GCP_PROJECT_ID,
    keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS_PATH,
  });
  

  
  const showsRef = db.collection(SHOW_COLLECTION).doc(comedian);
  const doc = await showsRef.get();
  return doc.get("shows")
}

export const getAllComedianDocuments = async () => {
  
}