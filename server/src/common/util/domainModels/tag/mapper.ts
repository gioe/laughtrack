import { GetTagResponseDTO, TagInterface } from "../../../models/interfaces/tag.interface.js"
import { UserInterface } from "../../../models/interfaces/user.interface.js"



export const toTagInterfaceArray = (payload: GetTagResponseDTO[]): TagInterface[] => {
    return payload.map((item: GetTagResponseDTO) => toTagInterface(item));
  }
  
  
export const toTagInterface = (payload: GetTagResponseDTO): TagInterface => {
  return {
    id: payload.id,
    name: payload.tag_name
  }
}

