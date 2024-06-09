export const getPropertyOfElements = (elements: Element[], property: string) => {
  return elements.map(element => element.getAttribute(property) ?? "")
}

export const getTextContent = (element: Element) => {
  return element.textContent;
}