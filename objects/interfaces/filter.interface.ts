export interface CheckboxOption {
    value: string;
    label: string;
    selected: boolean;
}

export interface FilterSection {
    id: string;
    name: string;
    options: CheckboxOption[];
}
