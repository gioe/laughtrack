export interface Selectable {
    id: number;
    displayName: string;
    selected?: boolean;
    value: string;
    select?: () => void;
}
