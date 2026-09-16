export function formatUserDate(value, timeZone = 'UTC', options = {}) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('ru-RU', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone,
    ...options,
  }).format(date)
}

export function dateKeyInTimeZone(value, timeZone = 'UTC') {
  if (!value) return ''
  const parts = partsInTimeZone(new Date(value), timeZone)
  return [parts.year, String(parts.month).padStart(2, '0'), String(parts.day).padStart(2, '0')].join('-')
}

function partsInTimeZone(date, timeZone) {
  return Object.fromEntries(
    new Intl.DateTimeFormat('en-US', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hourCycle: 'h23',
    }).formatToParts(date)
      .filter(({ type }) => type !== 'literal')
      .map(({ type, value }) => [type, Number(value)]),
  )
}

export function toDateTimeLocal(value, timeZone = 'UTC') {
  if (!value) return ''
  const parts = partsInTimeZone(new Date(value), timeZone)
  return [parts.year, String(parts.month).padStart(2, '0'), String(parts.day).padStart(2, '0')]
    .join('-') + `T${String(parts.hour).padStart(2, '0')}:${String(parts.minute).padStart(2, '0')}`
}

export function dateTimeLocalToIso(value, timeZone = 'UTC') {
  if (!value) return null
  const [datePart, timePart] = value.split('T')
  const [year, month, day] = datePart.split('-').map(Number)
  const [hour, minute] = timePart.split(':').map(Number)
  let timestamp = Date.UTC(year, month - 1, day, hour, minute)
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const actual = partsInTimeZone(new Date(timestamp), timeZone)
    const desired = Date.UTC(year, month - 1, day, hour, minute)
    const displayed = Date.UTC(actual.year, actual.month - 1, actual.day, actual.hour, actual.minute)
    timestamp += desired - displayed
  }
  return new Date(timestamp).toISOString()
}
