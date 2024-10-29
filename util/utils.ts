
import { clsx, type ClassValue } from "clsx"
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
  if (value) params.set(param, value)
  else params.delete(param);

  return params.toString();
}

const addOrRemoveCommaSeparatedValue = (params: URLSearchParams, param: string, value: string) => {
  const filters = params.get(param)
  let allValues = filters?.split(",") ?? []
  const valueIncluded = allValues.includes(value)

  if (!valueIncluded) {
    allValues.push(value)
  } else {
    allValues = allValues.filter((paramValues: string) => paramValues !== value);
  }

  if (allValues.length > 0) {
    params.set(param, allValues.join(","))
  } else {
    params.delete(param);
  }

  return params.toString();
}

