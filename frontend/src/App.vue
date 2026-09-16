<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Sidebar from './components/Sidebar.vue'
import CalendarView from './components/CalendarView.vue'
import NoteModal from './components/NoteModal.vue'
import ConfirmModal from './components/ConfirmModal.vue'
import ReminderModal from './components/ReminderModal.vue'
import UserSettingsModal from './components/UserSettingsModal.vue'
import { useNotesStore } from './stores/notes'
import { useTagsStore } from './stores/tags'
import { api, clearStoredEmail, getStoredEmail, setStoredEmail } from './stores/api'

const notesStore = useNotesStore()
const tagsStore = useTagsStore()
const isModalOpen = ref(false)
const editingNote = ref(null)
const toast = ref('')
const reminderToShow = ref(null)
const conflict = ref(false)
const confirmAction = ref(null)
const userEmail = ref(getStoredEmail())
const isSettingsOpen = ref(!userEmail.value)
const reminderTimer = ref(null)
const shownReminderKeys = new Set(JSON.parse(localStorage.getItem('shown_reminders') || '[]'))
const pendingReminderKeys = new Set()
const isFirstRun = computed(() => !userEmail.value)
const activeNotes = computed(() => notesStore.filteredNotes.filter((note) => note.is_active).length)
const noteEvents = computed(() => notesStore.filteredNotes.map((note) => {
  const eventColor = note.tags?.[0]?.color || '#3B82F6'
  return {
    title: note.title,
    start: note.target_datetime,
    id: note.id,
    backgroundColor: eventColor,
    borderColor: eventColor,
    color: '#FFFFFF',
    classNames: note.is_active ? ['note-event'] : ['note-event', 'note-event--done'],
    extendedProps: { note },
  }
}))
const upcomingGroups = computed(() => {
  const now = new Date()
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const endToday = new Date(startToday); endToday.setDate(endToday.getDate() + 1)
  const startWeek = new Date(startToday); startWeek.setDate(startWeek.getDate() - (startWeek.getDay() || 7) + 1)
  const endWeek = new Date(startWeek); endWeek.setDate(endWeek.getDate() + 7)
  const groups = { today: [], week: [], overdue: [] }
  notesStore.filteredNotes.filter((note) => note.is_active && note.target_datetime).forEach((note) => {
    const date = new Date(note.target_datetime)
    if (date < startToday) groups.overdue.push(note)
    else if (date < endToday) groups.today.push(note)
    else if (date < endWeek) groups.week.push(note)
  })
  return groups
})
watch(() => notesStore.selectedTagId, () => notesStore.loadNotes())
function openCreate(date = '') { editingNote.value = date ? { target_datetime: `${date}T09:00:00` } : null; isModalOpen.value = true }
function openEdit(note) { editingNote.value = note; isModalOpen.value = true }
async function saveNote(payload) { try { if (editingNote.value?.id) await notesStore.updateNote(editingNote.value.id, { ...payload, version: editingNote.value.version }); else await notesStore.createNote(payload); isModalOpen.value = false; conflict.value = false; toast.value = 'Заметка сохранена' } catch (error) { if (error.status === 409) conflict.value = true; else toast.value = error.message } }
async function moveNote(eventInfo) {
  const note = eventInfo.event.extendedProps.note
  const noteId = note.series_id || note.id
  try {
    await notesStore.updateNote(noteId, {
      target_datetime: eventInfo.event.start.toISOString(),
      version: note.version,
    })
    await notesStore.loadNotes({ tab: 'calendar' })
    toast.value = 'Заметка перенесена'
  } catch (error) {
    eventInfo.revert()
    toast.value = error.status === 409 ? 'Заметка была изменена в другом окне' : error.message
  }
}
function persistShownReminder(key) { shownReminderKeys.add(key); localStorage.setItem('shown_reminders', JSON.stringify([...shownReminderKeys])) }
function closeReminder() {
  if (!reminderToShow.value) return
  persistShownReminder(reminderToShow.value.key)
  pendingReminderKeys.delete(reminderToShow.value.key)
  reminderToShow.value = null
}
async function checkReminders() {
  if (!userEmail.value) return
  try {
    const activeNotes = await api('/api/notes?is_active=true')
    const now = Date.now()
    for (const note of activeNotes) {
      for (const reminder of note.reminders || []) {
        const key = `${note.id}:${reminder.id}:${reminder.remind_at}`
        if (new Date(reminder.remind_at).getTime() <= now && !shownReminderKeys.has(key) && !pendingReminderKeys.has(key)) {
          pendingReminderKeys.add(key)
          reminderToShow.value = { key, note, reminder }
          return
        }
      }
    }
  } catch {
    // Reminder polling should not interrupt the main note workflow.
  }
}
async function toggleNoteStatus(note) { try { await notesStore.updateNote(note.id, { is_active: !note.is_active, version: note.version }); isModalOpen.value = false; toast.value = note.is_active ? 'Заметка завершена' : 'Заметка возвращена в активные'; await notesStore.loadNotes() } catch (error) { toast.value = error.message } }
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
async function openCalendar() { await notesStore.loadNotes({ tab: 'calendar' }) }
async function openCompleted() { await notesStore.loadNotes({ tab: 'completed' }) }
async function openUpcoming() { await notesStore.loadNotes({ tab: 'upcoming' }) }
async function reloadConflict() { await notesStore.loadNotes(); editingNote.value = notesStore.notes.find((note) => note.id === editingNote.value?.id) || null; conflict.value = false }
async function addTag(payload) { try { await tagsStore.createTag(payload) } catch (error) { toast.value = error.message } }
async function updateTag(payload) { try { await tagsStore.updateTag(payload.id, { name: payload.name, color: payload.color }) } catch (error) { toast.value = error.message } }
async function loadAccountData() { await Promise.all([notesStore.loadNotes(), tagsStore.loadTags()]) }
function settingsSaved(email) { setStoredEmail(email); userEmail.value = email; isSettingsOpen.value = false; toast.value = 'Настройки сохранены' }
function switchAccount() { clearStoredEmail(); userEmail.value = ''; isSettingsOpen.value = true; notesStore.notes = []; tagsStore.tags = [] }
function requestDeleteTag(tag) {
  confirmAction.value = {
    type: 'tag',
    tag,
    title: 'Удалить тег?',
    message: `Тег «${tag.name}» будет удалён и отвязан от всех заметок.`,
    confirmLabel: 'Удалить тег',
  }
}
async function deleteTag() {
  const tag = confirmAction.value?.tag
  if (!tag) return
  try {
    await tagsStore.deleteTag(tag.id)
    if (notesStore.selectedTagId === tag.id) notesStore.selectedTagId = null
    await notesStore.loadNotes()
    confirmAction.value = null
    toast.value = 'Тег удалён'
  } catch (error) {
    toast.value = error.message
  }
}
watch(userEmail, (email, previousEmail) => {
  if (email && email !== previousEmail) loadAccountData()
}, { immediate: true })
onMounted(() => {
  checkReminders()
  reminderTimer.value = window.setInterval(checkReminders, 15000)
})
onUnmounted(() => window.clearInterval(reminderTimer.value))
</script>

<template>
  <div v-if="!isFirstRun" class="app-shell">
    <Sidebar :tags="tagsStore.tags" :selected-tag-id="notesStore.selectedTagId" :active-tab="notesStore.activeTab" :is-trash-view="notesStore.isTrashView" :note-count="notesStore.notes.length" @new-note="openCreate()" @open-trash="openTrash" @select-calendar="openCalendar" @select-completed="openCompleted" @select-upcoming="openUpcoming" @select-tag="notesStore.selectedTagId = $event" @add-tag="addTag" @update-tag="updateTag" @delete-tag="requestDeleteTag" />
    <main class="main-content">
      <header class="topbar"><div><p class="eyebrow">Рабочее пространство</p><h1>Мои заметки</h1></div><div class="topbar-actions"><label class="search"><span>⌕</span><input v-model="notesStore.searchQuery" placeholder="Поиск заметок" /></label><button class="settings-button" type="button" aria-label="Настройки" title="Настройки" @click="isSettingsOpen = true">⚙<span>Настройки</span></button><button class="avatar" type="button">Ф</button></div></header>
      <section class="calendar-toolbar"><div class="calendar-summary"><span class="summary-dot"></span>{{ activeNotes }} активных заметок</div></section>
      <div v-if="notesStore.error" class="error-banner">{{ notesStore.error }} <button type="button" @click="notesStore.loadNotes">Повторить</button></div>
      <section v-if="notesStore.activeTab === 'calendar'" class="calendar-wrap" :class="{ 'calendar-wrap--loading': notesStore.isLoading }"><CalendarView :events="noteEvents" @date-click="openCreate($event.dateStr)" @event-click="openEdit($event.event.extendedProps.note)" @event-drop="moveNote" /></section>
      <section v-else-if="notesStore.activeTab === 'upcoming'" class="notes-view" :class="{ 'trash-view--loading': notesStore.isLoading }"><div v-for="group in [{ title: 'Сегодня', notes: upcomingGroups.today }, { title: 'На этой неделе', notes: upcomingGroups.week }, { title: 'Прошедшие', notes: upcomingGroups.overdue }]" :key="group.title" class="notes-group"><h2>{{ group.title }}</h2><div v-if="!group.notes.length" class="notes-empty">Нет заметок</div><div v-else class="trash-grid"><article v-for="note in group.notes" :key="note.id" class="trash-card"><div class="trash-card__body"><h2>{{ note.title }}</h2><p>{{ note.text || 'Без текста' }}</p><time :datetime="note.target_datetime">{{ new Date(note.target_datetime).toLocaleString('ru-RU') }}</time></div><div class="trash-card__actions"><button class="button button--quiet" type="button" @click="openEdit(note)">Изменить</button><button class="button button--primary" type="button" @click="toggleNoteStatus(note)">Завершить</button></div></article></div></div></section>
      <section v-else-if="notesStore.activeTab === 'completed'" class="trash-view" :class="{ 'trash-view--loading': notesStore.isLoading }"><div v-if="!notesStore.filteredNotes.length && !notesStore.isLoading" class="trash-empty">Выполненных заметок нет</div><div v-else class="trash-grid"><article v-for="note in notesStore.filteredNotes" :key="note.id" class="trash-card"><div class="trash-card__body"><h2>{{ note.title }}</h2><p>{{ note.text || 'Без текста' }}</p><time :datetime="note.target_datetime || note.updated_at">{{ new Date(note.target_datetime || note.updated_at).toLocaleString('ru-RU') }}</time></div><div class="trash-card__actions"><button class="button button--quiet" type="button" @click="openEdit(note)">Изменить</button><button class="button button--primary" type="button" @click="toggleNoteStatus(note)">Вернуть в активные</button></div></article></div></section>
      <section v-else class="trash-view" :class="{ 'trash-view--loading': notesStore.isLoading }">
        <div v-if="!notesStore.filteredNotes.length && !notesStore.isLoading" class="trash-empty">Корзина пуста</div>
        <div v-else class="trash-grid">
          <article v-for="note in notesStore.filteredNotes" :key="note.id" class="trash-card">
            <div class="trash-card__body">
              <h2>{{ note.title }}</h2>
              <p>{{ note.text || 'Без текста' }}</p>
              <div v-if="note.tags?.length" class="note-tags" style="display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 14px;" aria-label="Теги заметки"><span v-for="tag in note.tags" :key="tag.id" class="note-tag" :style="{ color: tag.color || '#3B82F6', border: `1px solid ${tag.color || '#3B82F6'}`, borderRadius: '999px', padding: '3px 8px', backgroundColor: `${tag.color || '#3B82F6'}18`, fontSize: '10px', fontWeight: '700' }">{{ tag.name }}</span></div>
              <time :datetime="note.target_datetime || note.deleted_at || note.updated_at">{{ new Date(note.target_datetime || note.deleted_at || note.updated_at).toLocaleString('ru-RU') }}</time>
            </div>
            <div class="trash-card__actions">
              <button class="button button--quiet" type="button" @click="restoreNote(note)">Восстановить</button>
              <button class="button button--danger-outline" type="button" @click="requestPermanentDelete(note)">Удалить навсегда</button>
            </div>
          </article>
        </div>
      </section>
      <p v-if="notesStore.activeTab === 'calendar'" class="calendar-hint">Нажмите на свободный день, чтобы создать заметку</p>
    </main>
    <NoteModal v-model="isModalOpen" :note="editingNote" :tags="tagsStore.tags" :conflict="conflict" @save="saveNote" @delete="requestDelete" @toggle-status="toggleNoteStatus" @reload-current="reloadConflict" />
    <ReminderModal :model-value="Boolean(reminderToShow)" :reminder="reminderToShow" @close="closeReminder" />
    <UserSettingsModal v-model="isSettingsOpen" :first-run="isFirstRun" :current-email="userEmail" @saved="settingsSaved" @switch-account="switchAccount" />
    <ConfirmModal :model-value="Boolean(confirmAction)" :title="confirmAction?.title" :message="confirmAction?.message" :confirm-label="confirmAction?.confirmLabel" @update:model-value="confirmAction = null" @confirm="confirmAction?.type === 'tag' ? deleteTag() : confirmRequestedAction()" />
    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
  <UserSettingsModal v-else v-model="isSettingsOpen" :first-run="true" @saved="settingsSaved" />
</template>
