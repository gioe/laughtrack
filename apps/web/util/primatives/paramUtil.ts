export const formattedDateParam = (value: Date | undefined) => {
    if (!value) return "";
    return value.toISOString().split('T')[0];
};
