import { DateRange } from "@/objects/interface";

export interface ChipPreset {
    label: string;
    range: DateRange | undefined;
}

export const getChipPresets = (): ChipPreset[] => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const dayOfWeek = today.getDay();
    let weekendStart: Date;
    let weekendEnd: Date;
    if (dayOfWeek === 0) {
        weekendStart = today;
        weekendEnd = today;
    } else if (dayOfWeek === 6) {
        weekendStart = today;
        weekendEnd = new Date(today);
        weekendEnd.setDate(weekendEnd.getDate() + 1);
    } else {
        const daysUntilFriday = (5 - dayOfWeek + 7) % 7;
        weekendStart = new Date(today);
        weekendStart.setDate(weekendStart.getDate() + daysUntilFriday);
        weekendEnd = new Date(weekendStart);
        weekendEnd.setDate(weekendEnd.getDate() + 2);
    }

    const nextWeek = new Date(today);
    nextWeek.setDate(nextWeek.getDate() + 6);

    return [
        { label: "Any date", range: undefined },
        { label: "Tonight", range: { from: today, to: today } },
        { label: "Tomorrow", range: { from: tomorrow, to: tomorrow } },
        {
            label: "This Weekend",
            range: { from: weekendStart, to: weekendEnd },
        },
        { label: "Next 7 Days", range: { from: today, to: nextWeek } },
    ];
};
