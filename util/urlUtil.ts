export const generateUrl = (path: string): string => {
  return process.env.URL_DOMAIN + path
}