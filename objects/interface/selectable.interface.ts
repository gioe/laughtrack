export interface Selectable {
    id: number;
    displayName: string;
    value: string;
    selected?: boolean;
    select?: () => void;
}
