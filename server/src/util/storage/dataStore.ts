import { FieldValue, Firestore } from "@google-cloud/firestore"
import { Show } from "../../types/show.interface.js";
import { removeWhiteSpace } from "../string/stringUtil.js";

const db = new Firestore({
  projectId: process.env.GCP_PROJECT_ID,
  keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS_PATH,
});

export const updateDocument = async (documentReference: FirebaseFirestore.DocumentReference<FirebaseFirestore.DocumentData, FirebaseFirestore.DocumentData>, data: any) => {
  return documentReference.update({
    lastUpdate: new Date().toDateString(),
    data
});}
 
export const createNewDocument = async (documentReference: FirebaseFirestore.DocumentReference<FirebaseFirestore.DocumentData, FirebaseFirestore.DocumentData>, data: any) => {
  return documentReference.set({
        lastUpdate: new Date().toDateString(),
        data
  });
}

export const writeToFirestore = async (collectionName: string, documentName: string, data: any) => {
  const formattedDocName = removeWhiteSpace(documentName)
  const docRef = db.collection(collectionName).doc(formattedDocName);
  const comedianDoc = await docRef.get()

  if (comedianDoc.exists) {
    updateDocument(docRef, data)
  } else {
    createNewDocument(docRef, data)
  }
}

export const getValueFromAllDocuments = async (collectionName: string, value: string) => {
  const collectionRef = db.collection(collectionName)
  const allDocuments = await collectionRef.listDocuments();
  return Promise.all(allDocuments.map(docRef => getValueFromDocumentReference(docRef, value)));
}

export const getValueFromSpecificDocument = async (collectionName: string, docName: string, value: string) => {
  const doc = await db.collection(collectionName).doc(docName).get()
  return getValueFromDocument(doc, value);
}

const getValueFromDocumentReference = async (docRef: FirebaseFirestore.DocumentReference<FirebaseFirestore.DocumentData, FirebaseFirestore.DocumentData>, 
  value: string) => {
    const doc = await docRef.get();
    return getValueFromDocument(doc, value)
  }

const getValueFromDocument = (doc: FirebaseFirestore.DocumentSnapshot<FirebaseFirestore.DocumentData, FirebaseFirestore.DocumentData>, value: string) => {
  return {
    docName: doc.id,
    value: doc.get(value)
   };
  }
    