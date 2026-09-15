import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const api = async (path, options = {}) => {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}))
    const requestError = new Error(detail.detail || 'Не удалось выполнить запрос')
    requestError.status = response.status
    throw requestError
  }
  return response.status === 204 ? null : response.json()
}

export const useNotesStore = defineStore('notes', () => {
  const notes = ref([])
  const isLoading = ref(false)
  const error = ref('')
  const selectedTagId = ref(null)
  const showCompleted = ref(true)
  const isTrashView = ref(false)
  const searchQuery = ref('')
  const realtimeEnabled = false
  let socket = null
  let reconnectTimer = null

  function upsertNote(note) {
    const index = notes.value.findIndex((item) => item.id === note.id)
    if (index === -1) notes.value.unshift(note)
    else notes.value[index] = note
  }

  function connectWebSocket() {
    if (!realtimeEnabled || typeof window === 'undefined' || typeof window.WebSocket !== 'function') return
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    socket = new WebSocket(`${protocol}//${window.location.host}/ws`)
    socket.onmessage = ({ data }) => {
      const message = JSON.parse(data)
      if (message.event === 'note_created' || message.event === 'note_updated') upsertNote(message.note)
      if (message.event === 'note_deleted') notes.value = notes.value.filter((note) => note.id !== (message.note?.id || message.note_id))
    }
    socket.onclose = () => {
      reconnectTimer = window.setTimeout(connectWebSocket, 3000)
    }
  }

  const filteredNotes = computed(() => notes.value.filter((note) => {
    const matchesTag = !selectedTagId.value || note.tags?.some((tag) => tag.id === selectedTagId.value)
    const matchesStatus = showCompleted.value || note.is_active
    const query = searchQuery.value.trim().toLowerCase()
    const matchesSearch = !query || `${note.title} ${note.text}`.toLowerCase().includes(query)
    return matchesTag && matchesStatus && matchesSearch
  }))

  async function loadNotes({ trash = isTrashView.value } = {}) {
    isLoading.value = true
    error.value = ''
    try {
      isTrashView.value = trash
      if (trash) {
        notes.value = await api('/api/notes/trash')
        return
      }
      const params = new URLSearchParams()
      if (selectedTagId.value) params.set('tag_id', selectedTagId.value)
      if (!showCompleted.value) params.set('is_active', 'true')
      notes.value = await api(`/api/notes?${params}`)
    } catch (requestError) {
      error.value = requestError.message
    } finally {
      isLoading.value = false
    }
  }

  async function createNote(payload) {
    const note = await api('/api/notes', { method: 'POST', body: JSON.stringify(payload) })
    notes.value.unshift(note)
    return note
  }

  async function updateNote(id, payload) {
    const note = await api(`/api/notes/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
    const index = notes.value.findIndex((item) => item.id === id)
    if (index !== -1) notes.value[index] = note
    return note
  }

  async function deleteNote(id) {
    await api(`/api/notes/${id}`, { method: 'DELETE' })
    notes.value = notes.value.filter((note) => note.id !== id)
  }

  async function loadTrash() {
    await loadNotes({ trash: true })
  }

  async function restoreNote(id) {
    await api(`/api/notes/${id}/restore`, { method: 'POST' })
    notes.value = notes.value.filter((note) => note.id !== id)
  }

  async function permanentlyDeleteNote(id) {
    await api(`/api/notes/${id}/permanent`, { method: 'DELETE' })
    notes.value = notes.value.filter((note) => note.id !== id)
  }

  if (realtimeEnabled) connectWebSocket()

  return {
    notes, filteredNotes, isLoading, error, selectedTagId, showCompleted, isTrashView, searchQuery,
    loadNotes, loadTrash, createNote, updateNote, deleteNote, restoreNote, permanentlyDeleteNote,
  }
})
