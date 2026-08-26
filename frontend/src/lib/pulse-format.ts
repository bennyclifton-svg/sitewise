export function attentionHeadline(count: number): string {
  if (count === 0) return "Nothing needs attention";
  if (count === 1) return "1 item needs attention";
  return `${count} items need attention`;
}
