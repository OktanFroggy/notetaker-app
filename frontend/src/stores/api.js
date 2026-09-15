export function getStoredEmail() {
  return localStorage.getItem('user_email') || ''
}

export function setStoredEmail(email) {
  localStorage.setItem('user_email', email)
}

export function clearStoredEmail() {
  localStorage.removeItem('user_email')
}

export async function api(path, options = {}) {
  const email = options.email || getStoredEmail()
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(email ? { 'X-User-Email': email } : {}),
      ...(options.headers || {}),
    },
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}))
    const requestError = new Error(detail.detail || 'Не удалось выполнить запрос')
    requestError.status = response.status
    throw requestError
  }
  return response.status === 204 ? null : response.json()
}