export function formatDateTime(dateStr?: string | null): string {
  if (!dateStr) return "-"
  return new Date(dateStr).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
}

export function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "-"
  return new Date(dateStr).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })
}

export function formatTime(dateStr?: string | null): string {
  if (!dateStr) return "-"
  return new Date(dateStr).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  })
}