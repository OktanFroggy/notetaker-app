import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from './api'

export const useNotesStore = defineStore('notes', () => {
  const notes = ref([])
  const isLoading = ref(false)
  const error = ref('')
  const selectedTagId = ref(null)
  const activeTab = ref('calendar')
  const searchQuery = ref('')
  const realtimeEnabled = true
  let socket = null
  let reconnectTimer = null
  let connectedEmail = ''

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
    socket = new WebSocket(`${protocol}//${window.location.host}/ws?${query}`)
    socket.onmessage = ({ data }) => {
      const message = JSON.parse(data)
      if (message.event === 'note_created' || message.event === 'note_updated') {
        void loadNotes({ tab: activeTab.value })
      }
      if (message.event === 'note_deleted') {
        const deletedId = message.note?.id || message.note_id
        notes.value = notes.value.filter((note) => note.id !== deletedId && note.series_id !== deletedId)
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

  const filteredNotes = computed(() => notes.value.filter((note) => {
    const matchesTag = !selectedTagId.value || note.tags?.some((tag) => tag.id === selectedTagId.value)
    const query = searchQuery.value.trim().toLowerCase()
    const matchesSearch = !query || `${note.title} ${note.text}`.toLowerCase().includes(query)
    return matchesTag && matchesSearch
  }))

  async function loadNotes({ tab = activeTab.value } = {}) {
    isLoading.value = true
    error.value = ''
    try {
      activeTab.value = tab
      if (tab === 'trash') {
        notes.value = await api('/api/notes/trash')
        return
      }
      const params = new URLSearchParams()
      if (selectedTagId.value) params.set('tag_id', selectedTagId.value)
      params.set('is_active', tab === 'completed' ? 'false' : 'true')
      if (tab === 'calendar') params.set('expand_recurrences', 'true')
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
    await loadNotes({ tab: 'trash' })
  }

  async function restoreNote(id) {
    await api(`/api/notes/${id}/restore`, { method: 'POST' })
    notes.value = notes.value.filter((note) => note.id !== id)
  }

  async function permanentlyDeleteNote(id) {
    await api(`/api/notes/${id}/permanent`, { method: 'DELETE' })
    notes.value = notes.value.filter((note) => note.id !== id)
  }

  const isTrashView = computed(() => activeTab.value === 'trash')

  return {
    notes, filteredNotes, isLoading, error, selectedTagId, activeTab, isTrashView, searchQuery,
    loadNotes, loadTrash, createNote, updateNote, deleteNote, restoreNote, permanentlyDeleteNote,
    connectRealtime, disconnectRealtime,
  }
})
