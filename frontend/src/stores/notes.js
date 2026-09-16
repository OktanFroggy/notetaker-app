import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from './api'

function isOccurrenceId(value) {
  return typeof value === 'string' && /^\d+(?:_virtual_|_)\d{4}-\d{2}-\d{2}/.test(value)
}

export function resolveMasterNoteId(noteOrId) {
  const value = typeof noteOrId === 'object' && noteOrId !== null
    ? (noteOrId.series_id || noteOrId.id)
    : noteOrId
  if (isOccurrenceId(value)) return Number(value.split(/_virtual_|_/)[0])
  return Number(value)
}

export const useNotesStore = defineStore('notes', () => {
  const notes = ref([])
  const isLoading = ref(false)
  const error = ref('')
  const selectedTagId = ref(null)
  const activeTab = ref('calendar')
  const searchQuery = ref('')
  const listTargetFrom = ref('')
  const listTargetTo = ref('')
  const listStatus = ref('all')
  const listTagIds = ref([])
  const listSortBy = ref('updated_at_desc')
  const listPageSize = 100
  const listHasMore = ref(false)
  const realtimeEnabled = true
  let socket = null
  let reconnectTimer = null
  let connectedEmail = ''
  const reminderDismissedListeners = new Set()

  function upsertNote(note) {
    const index = notes.value.findIndex((item) => item.id === note.id)
    if (index === -1) notes.value.unshift(note)
    else notes.value[index] = note
  }

  function connectWebSocket() {
    if (!realtimeEnabled || !connectedEmail || typeof window === 'undefined' || typeof window.WebSocket !== 'function') return
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const query = new URLSearchParams({ email: connectedEmail })
    const backendPort = window.location.port === '5173' ? '8000' : window.location.port
    const backendHost = backendPort ? `${window.location.hostname}:${backendPort}` : window.location.hostname
    socket = new WebSocket(`${protocol}//${backendHost}/ws?${query}`)
    socket.onmessage = ({ data }) => {
      const message = JSON.parse(data)
      if (message.event === 'note_created' || message.event === 'note_updated') {
        void loadNotes({ tab: activeTab.value })
      }
      if (message.event === 'note_deleted') {
        const deletedId = message.note?.id || message.note_id
        notes.value = notes.value.filter((note) => note.id !== deletedId && note.series_id !== deletedId)
      }
      if (message.event === 'reminder_dismissed') {
        reminderDismissedListeners.forEach((listener) => listener(message.reminder_key))
      }
    }
    socket.onclose = () => {
      socket = null
      if (realtimeEnabled && connectedEmail) reconnectTimer = window.setTimeout(connectWebSocket, 3000)
    }
  }

  function connectRealtime(email) {
    if (!realtimeEnabled || !email) return
    window.clearTimeout(reconnectTimer)
    if (socket) {
      socket.onclose = null
      socket.close()
      socket = null
    }
    connectedEmail = email
    connectWebSocket()
  }

  function disconnectRealtime() {
    connectedEmail = ''
    window.clearTimeout(reconnectTimer)
    if (socket) {
      socket.onclose = null
      socket.close()
      socket = null
    }
  }

  function sendReminderDismissed(reminderKey) {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ event: 'reminder_dismissed', reminder_key: reminderKey }))
    }
  }

  function onReminderDismissed(listener) {
    reminderDismissedListeners.add(listener)
    return () => reminderDismissedListeners.delete(listener)
  }

  const filteredNotes = computed(() => notes.value.filter((note) => {
    const matchesTag = !selectedTagId.value || note.tags?.some((tag) => tag.id === selectedTagId.value)
    const query = searchQuery.value.trim().toLowerCase()
    const matchesSearch = !query || `${note.title} ${note.text}`.toLowerCase().includes(query)
    return matchesTag && matchesSearch
  }))

  async function loadNotes({ tab = activeTab.value, append = false } = {}) {
    isLoading.value = true
    error.value = ''
    try {
      activeTab.value = tab
      if (tab === 'trash') {
        notes.value = await api('/api/notes/trash')
        return
      }
      const params = new URLSearchParams()
      if (tab === 'list') {
        const offset = append ? notes.value.length : 0
        if (searchQuery.value.trim()) params.set('search', searchQuery.value.trim())
        listTagIds.value.forEach((tagId) => params.append('tag_ids', tagId))
        if (listStatus.value !== 'all') params.set('is_active', listStatus.value === 'active' ? 'true' : 'false')
        if (listTargetFrom.value) params.set('target_from', `${listTargetFrom.value}T00:00:00`)
        if (listTargetTo.value) params.set('target_to', `${listTargetTo.value}T23:59:59`)
        params.set('sort_by', listSortBy.value)
        params.set('offset', String(offset))
        params.set('limit', String(listPageSize))
      } else {
        if (selectedTagId.value) params.set('tag_id', selectedTagId.value)
        params.set('is_active', tab === 'completed' ? 'false' : 'true')
      }
      if (tab === 'calendar') params.set('expand_recurrences', 'true')
      const loadedNotes = await api(`/api/notes?${params}`)
      if (tab === 'list' && append) notes.value = [...notes.value, ...loadedNotes]
      else notes.value = loadedNotes
      if (tab === 'list') listHasMore.value = loadedNotes.length === listPageSize
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
    const masterId = resolveMasterNoteId(id)
    const endpointId = isOccurrenceId(id) ? id : masterId
    const note = await api(`/api/notes/${endpointId}`, { method: 'PUT', body: JSON.stringify(payload) })
    const index = notes.value.findIndex((item) => item.id === id || item.id === masterId || item.series_id === masterId)
    if (index !== -1) notes.value[index] = note
    return note
  }

  async function deleteNote(id) {
    const masterId = resolveMasterNoteId(id)
    const endpointId = isOccurrenceId(id) ? id : masterId
    await api(`/api/notes/${endpointId}`, { method: 'DELETE' })
    notes.value = notes.value.filter((note) => note.id !== id && note.id !== masterId && note.series_id !== masterId)
  }

  async function loadTrash() {
    await loadNotes({ tab: 'trash' })
  }

  async function restoreNote(id) {
    const endpointId = isOccurrenceId(id) ? id : resolveMasterNoteId(id)
    await api(`/api/notes/${endpointId}/restore`, { method: 'POST' })
    notes.value = notes.value.filter((note) => note.id !== id)
  }

  async function permanentlyDeleteNote(id) {
    const masterId = resolveMasterNoteId(id)
    const endpointId = isOccurrenceId(id) ? id : masterId
    await api(`/api/notes/${endpointId}/permanent`, { method: 'DELETE' })
    notes.value = notes.value.filter((note) => (
      note.id !== id && note.id !== masterId && note.series_id !== masterId
    ))
  }

  const isTrashView = computed(() => activeTab.value === 'trash')

  return {
    notes, filteredNotes, isLoading, error, selectedTagId, activeTab, isTrashView, searchQuery,
    listTargetFrom, listTargetTo, listStatus, listTagIds, listSortBy, listHasMore,
    loadNotes, loadTrash, createNote, updateNote, deleteNote, restoreNote, permanentlyDeleteNote,
    connectRealtime, disconnectRealtime, sendReminderDismissed, onReminderDismissed,
  }
})
