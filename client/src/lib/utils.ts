
import { clsx, type ClassValue } from "clsx"
import { usePathname, useSearchParams } from "next/navigation";
import { useRouter } from "next/router";
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function capitalizeFirstLetter(string?: string) {
  if (string !== undefined) {
    return string.charAt(0).toUpperCase() + string.slice(1);
  }
}

export function handleUrlParams(searchParams: URLSearchParams, param: string, value: string | number): string {

  console.log(`Editing ${param} param with value: ${value}`)

  const stringParam = value.toString();
  const params = new URLSearchParams(searchParams)

  switch (param) {
    case 'sort': return addOrRemoveSingleValue(params, param, stringParam)
    case 'query': return addOrRemoveSingleValue(params, param, stringParam)
    case 'page': return addOrRemoveSingleValue(params, param, stringParam)
    default: return addOrRemoveCommaSeparatedValue(params, param, stringParam)
  }
  
}

const addOrRemoveSingleValue = (params: URLSearchParams, param: string, value: string) => {
  if (value) {
    params.set(param, value);
  } else {
    params.delete(param);
  }
  return params.toString();
}

const addOrRemoveCommaSeparatedValue = (params: URLSearchParams, param: string, value: string) => {
  return ""
}

