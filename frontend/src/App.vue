<script setup>
import { computed, ref, watch } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import ruLocale from '@fullcalendar/core/locales/ru'
import Sidebar from './components/Sidebar.vue'
import NoteModal from './components/NoteModal.vue'
import ConfirmModal from './components/ConfirmModal.vue'
import { useNotesStore } from './stores/notes'
import { useTagsStore } from './stores/tags'

const notesStore = useNotesStore()
const tagsStore = useTagsStore()
const isModalOpen = ref(false)
const editingNote = ref(null)
const toast = ref('')
const conflict = ref(false)
const confirmAction = ref(null)
const activeNotes = computed(() => notesStore.filteredNotes.filter((note) => note.is_active).length)
const noteEvents = computed(() => notesStore.filteredNotes.map((note) => ({
  title: note.title,
  start: note.date_time || note.created_at || note.target_datetime,
  id: note.id,
  classNames: note.is_active ? ['note-event'] : ['note-event', 'note-event--done'],
  extendedProps: { note },
})))
const calendarOptions = computed(() => ({
  initialView: 'dayGridMonth',
  plugins: [dayGridPlugin, interactionPlugin],
  locales: [ruLocale],
  locale: 'ru',
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: '',
  },
  dayMaxEvents: 3,
  fixedWeekCount: false,
  dateClick: (info) => openCreate(info.dateStr),
  eventClick: (info) => openEdit(info.event.extendedProps.note),
}))

watch([() => notesStore.selectedTagId, () => notesStore.showCompleted], () => notesStore.loadNotes())
function openCreate(date = '') { editingNote.value = date ? { target_datetime: `${date}T09:00:00` } : null; isModalOpen.value = true }
function openEdit(note) { editingNote.value = note; isModalOpen.value = true }
async function saveNote(payload) { try { if (editingNote.value?.id) await notesStore.updateNote(editingNote.value.id, { ...payload, version: editingNote.value.version }); else await notesStore.createNote(payload); isModalOpen.value = false; conflict.value = false; toast.value = 'Заметка сохранена' } catch (error) { if (error.status === 409) conflict.value = true; else toast.value = error.message } }
function requestDelete(note) {
  confirmAction.value = { type: 'delete', note, title: 'Переместить заметку в корзину?', message: `Заметка «${note.title}» будет перемещена в корзину.`, confirmLabel: 'Удалить' }
}
function requestPermanentDelete(note) {
  confirmAction.value = { type: 'permanent', note, title: 'Удалить навсегда?', message: 'Вы уверены? Это действие нельзя отменить', confirmLabel: 'Удалить' }
}
async function confirmRequestedAction() {
  const action = confirmAction.value
  if (!action) return
  try {
    if (action.type === 'permanent') {
      await notesStore.permanentlyDeleteNote(action.note.id)
      toast.value = 'Заметка удалена навсегда'
    } else {
      await notesStore.deleteNote(action.note.id)
      isModalOpen.value = false
      toast.value = 'Заметка перемещена в корзину'
    }
    confirmAction.value = null
  } catch (error) {
    toast.value = error.message
  }
}
async function restoreNote(note) {
  try {
    await notesStore.restoreNote(note.id)
    toast.value = 'Заметка восстановлена'
  } catch (error) {
    toast.value = error.message
  }
}
async function openTrash() { await notesStore.loadTrash() }
async function openCalendar() { await notesStore.loadNotes({ trash: false }) }
async function reloadConflict() { await notesStore.loadNotes(); editingNote.value = notesStore.notes.find((note) => note.id === editingNote.value?.id) || null; conflict.value = false }
async function addTag(payload) { try { await tagsStore.createTag(payload) } catch (error) { toast.value = error.message } }
Promise.all([notesStore.loadNotes(), tagsStore.loadTags()])
</script>

<template>
  <div class="app-shell">
    <Sidebar :tags="tagsStore.tags" :selected-tag-id="notesStore.selectedTagId" :show-completed="notesStore.showCompleted" :is-trash-view="notesStore.isTrashView" :note-count="notesStore.notes.length" @new-note="openCreate()" @open-trash="openTrash" @select-calendar="openCalendar" @select-tag="notesStore.selectedTagId = $event" @toggle-completed="notesStore.showCompleted = $event" @add-tag="addTag" />
    <main class="main-content">
      <header class="topbar"><div><p class="eyebrow">Рабочее пространство</p><h1>Мои заметки</h1></div><div class="topbar-actions"><label class="search"><span>⌕</span><input v-model="notesStore.searchQuery" placeholder="Поиск заметок" /></label><button class="avatar" type="button">Ф</button></div></header>
      <section class="calendar-toolbar"><div class="calendar-summary"><span class="summary-dot"></span>{{ activeNotes }} активных заметок</div></section>
      <div v-if="notesStore.error" class="error-banner">{{ notesStore.error }} <button type="button" @click="notesStore.loadNotes">Повторить</button></div>
      <section v-if="!notesStore.isTrashView" class="calendar-wrap" :class="{ 'calendar-wrap--loading': notesStore.isLoading }"><FullCalendar :options="{ ...calendarOptions, events: noteEvents }" /></section>
      <section v-else class="trash-view" :class="{ 'trash-view--loading': notesStore.isLoading }">
        <div v-if="!notesStore.filteredNotes.length && !notesStore.isLoading" class="trash-empty">Корзина пуста</div>
        <div v-else class="trash-grid">
          <article v-for="note in notesStore.filteredNotes" :key="note.id" class="trash-card">
            <div class="trash-card__body">
              <h2>{{ note.title }}</h2>
              <p>{{ note.text || 'Без текста' }}</p>
              <time :datetime="note.target_datetime || note.deleted_at || note.updated_at">{{ new Date(note.target_datetime || note.deleted_at || note.updated_at).toLocaleString('ru-RU') }}</time>
            </div>
            <div class="trash-card__actions">
              <button class="button button--quiet" type="button" @click="restoreNote(note)">Восстановить</button>
              <button class="button button--danger-outline" type="button" @click="requestPermanentDelete(note)">Удалить навсегда</button>
            </div>
          </article>
        </div>
      </section>
      <p v-if="!notesStore.isTrashView" class="calendar-hint">Нажмите на свободный день, чтобы создать заметку</p>
    </main>
    <NoteModal v-model="isModalOpen" :note="editingNote" :tags="tagsStore.tags" :conflict="conflict" @save="saveNote" @delete="requestDelete" @reload-current="reloadConflict" />
    <ConfirmModal :model-value="Boolean(confirmAction)" :title="confirmAction?.title" :message="confirmAction?.message" :confirm-label="confirmAction?.confirmLabel" @update:model-value="confirmAction = null" @confirm="confirmRequestedAction" />
    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>
