"use client";

import {
    dateWithOrdinalFromMoment,
    monthFromMoment,
} from "../../util/dateUtil";

interface DateMarqueeProps {
    date: moment.Moment;
}

const DateMarquee = ({ date }: DateMarqueeProps) => {
    return (
        <div className="flex flex-col">
            <h1 className="font-fjalla text-copper text-2xl text-center">
                {`${monthFromMoment(date)}`}
            </h1>
            <h1 className="font-fjalla text-copper text-2xl text-center">
                {`${dateWithOrdinalFromMoment(date)}`}
            </h1>
        </div>
    );
};

export default DateMarquee;
