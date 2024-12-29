export function isToday(date: Date) {
    const today = new Date();
    return date.getDate() === today.getDate() &&
        date.getMonth() === today.getMonth() &&
        date.getFullYear() === today.getFullYear();
}

export function isTomorrow(date: Date) {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1); // Increment tomorrow's date by one day

    return date.getDate() === tomorrow.getDate() &&
        date.getMonth() === tomorrow.getMonth() &&
        date.getFullYear() === tomorrow.getFullYear();
}

export function datesAreSame(date1: Date, date2: Date) {
    return date1.getFullYear() === date2.getFullYear() &&
        date1.getMonth() === date2.getMonth() &&
        date1.getDate() === date2.getDate();
}

export function datesAreToday(date1: Date, date2: Date) {
    return datesAreSame(date1, date2) && isToday(date1)
}

export function datesAreTomorrow(date1: Date, date2: Date) {
    return datesAreSame(date1, date2) && isTomorrow(date1)

}

