
import { CityDTO, CityInterface } from "./city.interface";

export class City implements CityInterface {
    id: number;
    name: string;

    constructor(input: CityDTO) {
        this.id = input.id;
        this.name = input.name;
    }

    toSelectableItem() {
        return {
            id: this.id,
            name: this.name,
        };
    }

}
