import {
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  sendEmailVerification,
  sendPasswordResetEmail,
  signInWithPopup,
  updatePassword,
  signInWithEmailAndPassword,
  onAuthStateChanged, 
} from "firebase/auth";
import { auth } from "./firebaseConfig";

export const doSignOut = () => {
    return auth.signOut();
}

export const doSendEmailVerification = () => {
    return sendEmailVerification(auth.currentUser, {
        url: `${window.location.origin}/home`,
    });
}

export const doSignInWithEmailAndPassword = (email, password) => {
  return signInWithEmailAndPassword(auth, email, password);
};

export const onAuthStateChange = (callback) => {
  return onAuthStateChanged(auth, callback);
};