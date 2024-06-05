export const getOptionsProperty = (options: Element[], property: string) => {
  return options.map(option => option.getAttribute(property) ?? "")
}

export const getTextContent = (element: Element) => {
  return element.textContent;
}