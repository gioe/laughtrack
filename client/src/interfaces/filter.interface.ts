export interface FilterOption {
  value: string;
  label: string;
  selected: boolean;
}

export interface Filter {
  id: string,
  name: string,
  options: FilterOption[]
}