import { FieldValue, Firestore } from "@google-cloud/firestore"
import { Show } from "../../types/show.interface.js";
import { removeWhiteSpace } from "../string/stringUtil.js";

const SHOW_COLLECTION_NAME = 'shows'

const db = new Firestore({
  projectId: process.env.GCP_PROJECT_ID,
  keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS_PATH,
});

export const writeToFirestore = async (shows: Show[]) => {
  
  for (const show of shows) {
    for (const comedian of show.comedians) {
      const comedianDocTitle = removeWhiteSpace(comedian.name.toLowerCase());
     
      const comedianDocRef = db.collection(SHOW_COLLECTION_NAME).doc(comedianDocTitle);
      const comedianDoc = comedianDocRef.get()

      if ((await comedianDoc).exists) {
        comedianDocRef.update(
          {
            shows: FieldValue.arrayUnion({
              dateTime: show.dateTime,
              showName: show.name,
              ticketLink: show.ticketLink
          })
        });
      } else {
        comedianDocRef.set({
          lastUpdate: new Date().toDateString(),
          comedian: comedian.name, 
          website: comedian.website ?? "",
          shows: FieldValue.arrayUnion({
            dateTime: show.dateTime,
            showName: show.name,
            ticketLink: show.ticketLink
          })
        });
      }
    }
  }
}

export const getComedianShowDocuments = async (comedian: string) => {
  const showsRef = db.collection(SHOW_COLLECTION_NAME).doc(comedian);
  const doc = await showsRef.get();
  return doc.get('shows')
}

export const getAllComedianDocuments = async () => {
  const showsRef = db.collection(SHOW_COLLECTION_NAME)
  const allDocuments = await showsRef.listDocuments();
  return Promise.all(allDocuments.map(doc => getValue(doc, "comedian")));
}

const getValue = async (docRef: FirebaseFirestore.DocumentReference<FirebaseFirestore.DocumentData, FirebaseFirestore.DocumentData>, 
  valueName: string) => {
    const doc = await docRef.get();
   return {
    docName: doc.id,
    comedianName: doc.get(valueName)
   };
}