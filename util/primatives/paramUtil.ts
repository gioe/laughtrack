export const formattedDateParam = (value: Date | undefined) => {
    if  (!value) return "";
    const monthDay = value.getDate().toString();
    const month = (value.getMonth() + 1).toString();
    const year = value.getFullYear().toString();
    return `${year}-${month}-${monthDay}`;
};
