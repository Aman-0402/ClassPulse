// Backend TimeField serializes as "HH:MM:SS" — render as a 12-hour clock label.
export function formatTime(value: string): string {
  const [hourStr, minuteStr] = value.split(":");
  const hour = Number(hourStr);
  const minute = Number(minuteStr);
  const period = hour >= 12 ? "PM" : "AM";
  const displayHour = hour % 12 === 0 ? 12 : hour % 12;
  return `${displayHour}:${String(minute).padStart(2, "0")} ${period}`;
}

// Backend DateTimeField serializes as a full ISO string — render as a 12-hour clock label.
export function formatSessionTime(isoDatetime: string): string {
  return new Date(isoDatetime).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}
