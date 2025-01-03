export interface Selectable {
    id: number;
    display: string;
    value: string;
    selected?: boolean;
    select?: () => void;
}
