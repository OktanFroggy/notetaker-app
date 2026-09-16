<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Sidebar from './components/Sidebar.vue'
import CalendarView from './components/CalendarView.vue'
import NoteModal from './components/NoteModal.vue'
import ConfirmModal from './components/ConfirmModal.vue'
import ReminderModal from './components/ReminderModal.vue'
import UserSettingsModal from './components/UserSettingsModal.vue'
import { resolveMasterNoteId, useNotesStore } from './stores/notes'
import { useTagsStore } from './stores/tags'
import { useUserSettingsStore } from './stores/userSettings'
import { api, clearStoredEmail, getStoredEmail, setStoredEmail } from './stores/api'
import { dateKeyInTimeZone, formatUserDate } from './utils/dates'

const notesStore = useNotesStore()
const tagsStore = useTagsStore()
const userSettingsStore = useUserSettingsStore()
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
let listFilterTimer = null
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
  const todayKey = dateKeyInTimeZone(now, userSettingsStore.timezone)
  const startToday = new Date(`${todayKey}T00:00:00Z`)
  const endToday = new Date(startToday); endToday.setUTCDate(endToday.getUTCDate() + 1)
  const startWeek = new Date(startToday); startWeek.setUTCDate(startWeek.getUTCDate() - (startWeek.getUTCDay() || 7) + 1)
  const endWeek = new Date(startWeek); endWeek.setUTCDate(endWeek.getUTCDate() + 7)
  const groups = { today: [], week: [], overdue: [] }
  notesStore.filteredNotes.filter((note) => note.is_active && note.target_datetime).forEach((note) => {
    const date = new Date(`${dateKeyInTimeZone(note.target_datetime, userSettingsStore.timezone)}T00:00:00Z`)
    if (date < startToday) groups.overdue.push(note)
    else if (date < endToday) groups.today.push(note)
    else if (date < endWeek) groups.week.push(note)
  })
  return groups
})
watch(() => notesStore.selectedTagId, () => notesStore.loadNotes())
watch(
  () => [
    notesStore.searchQuery,
    notesStore.listTargetFrom,
    notesStore.listTargetTo,
    notesStore.listStatus,
    notesStore.listTagIds.slice(),
    notesStore.listSortBy,
  ],
  () => {
    if (notesStore.activeTab !== 'list') return
    window.clearTimeout(listFilterTimer)
    listFilterTimer = window.setTimeout(() => notesStore.loadNotes({ tab: 'list' }), 250)
  },
)
function openCreate(date = '') { editingNote.value = date ? { target_datetime: `${date}T09:00:00` } : null; isModalOpen.value = true }
function openEdit(note) { editingNote.value = note; isModalOpen.value = true }
function noteEndpointId(note) { return note?.occurrence_id || (typeof note?.id === 'string' && /^\d+(?:_virtual_|_)\d{4}-\d{2}-\d{2}/.test(note.id) ? note.id : resolveMasterNoteId(note)) }
async function saveNote(payload) { try { if (editingNote.value?.id) await notesStore.updateNote(noteEndpointId(editingNote.value), { ...payload, version: editingNote.value.version }); else await notesStore.createNote(payload); isModalOpen.value = false; conflict.value = false; toast.value = 'Заметка сохранена' } catch (error) { if (error.status === 409) conflict.value = true; else toast.value = error.message } }
async function moveNote(eventInfo) {
  const { info, note } = eventInfo
  const noteId = note.occurrence_id || resolveMasterNoteId(note)
  try {
    await notesStore.updateNote(noteId, {
      target_datetime: info.event.start.toISOString(),
      version: note.version,
    })
    await notesStore.loadNotes({ tab: 'calendar' })
    toast.value = 'Заметка перенесена'
  } catch (error) {
    info.revert()
    toast.value = error.status === 409 ? 'Заметка была изменена в другом окне' : error.message
  }
}
function persistShownReminder(key) { shownReminderKeys.add(key); localStorage.setItem('shown_reminders', JSON.stringify([...shownReminderKeys])) }
function closeReminder() {
  if (!reminderToShow.value) return
  const reminderKey = reminderToShow.value.key
  persistShownReminder(reminderKey)
  notesStore.sendReminderDismissed(reminderKey)
  pendingReminderKeys.delete(reminderKey)
  reminderToShow.value = null
}
function handleReminderDismissed(reminderKey) {
  if (!reminderKey) return
  persistShownReminder(reminderKey)
  pendingReminderKeys.delete(reminderKey)
  if (reminderToShow.value?.key === reminderKey) reminderToShow.value = null
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
async function toggleNoteStatus(note) { try { await notesStore.updateNote(noteEndpointId(note), { is_active: !note.is_active, version: note.version }); isModalOpen.value = false; toast.value = note.is_active ? 'Заметка завершена' : 'Заметка возвращена в активные'; await notesStore.loadNotes() } catch (error) { toast.value = error.message } }
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
      await notesStore.permanentlyDeleteNote(noteEndpointId(action.note))
      toast.value = 'Заметка удалена навсегда'
    } else {
      await notesStore.deleteNote(noteEndpointId(action.note))
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
async function openList() { await notesStore.loadNotes({ tab: 'list' }) }
async function openCompleted() { await notesStore.loadNotes({ tab: 'completed' }) }
async function openUpcoming() { await notesStore.loadNotes({ tab: 'upcoming' }) }
async function reloadConflict() { await notesStore.loadNotes(); editingNote.value = notesStore.notes.find((note) => note.id === editingNote.value?.id) || null; conflict.value = false }
async function addTag(payload) { try { await tagsStore.createTag(payload) } catch (error) { toast.value = error.message } }
async function updateTag(payload) { try { await tagsStore.updateTag(payload.id, { name: payload.name, color: payload.color }) } catch (error) { toast.value = error.message } }
async function loadAccountData() {
  notesStore.connectRealtime(userEmail.value)
  await Promise.all([userSettingsStore.load(), notesStore.loadNotes(), tagsStore.loadTags()])
}
function settingsSaved(settings) {
  setStoredEmail(settings.email)
  userEmail.value = settings.email
  userSettingsStore.setSettings(settings)
  isSettingsOpen.value = false
  toast.value = 'Настройки сохранены'
}
function switchAccount() { notesStore.disconnectRealtime(); clearStoredEmail(); userEmail.value = ''; isSettingsOpen.value = true; notesStore.notes = []; tagsStore.tags = [] }
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
  window.__removeReminderDismissedListener = notesStore.onReminderDismissed(handleReminderDismissed)
})
onUnmounted(() => {
  window.clearInterval(reminderTimer.value)
  window.clearTimeout(listFilterTimer)
  window.__removeReminderDismissedListener?.()
})
</script>

<template>
  <div v-if="!isFirstRun" class="app-shell">
    <Sidebar :tags="tagsStore.tags" :selected-tag-id="notesStore.selectedTagId" :active-tab="notesStore.activeTab" :is-trash-view="notesStore.isTrashView" :note-count="notesStore.notes.length" @new-note="openCreate()" @open-trash="openTrash" @select-calendar="openCalendar" @select-list="openList" @select-completed="openCompleted" @select-upcoming="openUpcoming" @select-tag="notesStore.selectedTagId = $event" @add-tag="addTag" @update-tag="updateTag" @delete-tag="requestDeleteTag" />
    <main class="main-content">
      <header class="topbar"><div><p class="eyebrow">Рабочее пространство</p><h1>Мои заметки</h1></div><div class="topbar-actions"><label class="search"><span>⌕</span><input v-model="notesStore.searchQuery" placeholder="Поиск заметок" /></label><button class="settings-button" type="button" aria-label="Настройки" title="Настройки" @click="isSettingsOpen = true">⚙<span>Настройки</span></button><button class="avatar" type="button">Ф</button></div></header>
      <section class="calendar-toolbar"><div class="calendar-summary"><span class="summary-dot"></span>{{ activeNotes }} активных заметок</div></section>
      <div v-if="notesStore.error" class="error-banner">{{ notesStore.error }} <button type="button" @click="notesStore.loadNotes">Повторить</button></div>
      <section v-if="notesStore.activeTab === 'calendar'" class="calendar-wrap" :class="{ 'calendar-wrap--loading': notesStore.isLoading }"><CalendarView :events="noteEvents" @date-click="openCreate($event.dateStr)" @event-click="openEdit($event.note)" @event-drop="moveNote" /></section>
      <section v-else-if="notesStore.activeTab === 'list'" class="notes-view">
        <div class="list-filters">
          <label class="field-label">С даты<input v-model="notesStore.listTargetFrom" type="date" /></label>
          <label class="field-label">По дату<input v-model="notesStore.listTargetTo" type="date" /></label>
          <label class="field-label">Статус<select v-model="notesStore.listStatus"><option value="all">Все</option><option value="active">Активные</option><option value="inactive">Деактивированные</option></select></label>
          <label class="field-label">Сортировка<select v-model="notesStore.listSortBy"><option value="event_date_asc">Дата заметки: сначала ранние</option><option value="event_date_desc">Дата заметки: сначала поздние</option><option value="updated_at_desc">Дата изменения: новые</option></select></label>
        </div>
        <fieldset class="tag-picker list-tag-picker"><legend>Теги</legend><label v-for="tag in tagsStore.tags" :key="tag.id" class="tag-check"><input v-model="notesStore.listTagIds" :value="tag.id" type="checkbox" />{{ tag.name }}</label><span v-if="!tagsStore.tags.length" class="muted">Теги пока не созданы</span></fieldset>
        <div v-if="!notesStore.notes.length && !notesStore.isLoading" class="notes-empty">Заметки не найдены</div>
        <div v-else class="trash-grid"><article v-for="note in notesStore.notes" :key="note.id" class="trash-card"><div class="trash-card__body"><h2>{{ note.title }}</h2><p>{{ note.text || 'Без текста' }}</p><time :datetime="note.target_datetime || note.updated_at">{{ formatUserDate(note.target_datetime || note.updated_at, userSettingsStore.timezone) }}</time></div><div class="trash-card__actions"><button class="button button--quiet" type="button" @click="openEdit(note)">Изменить</button><button class="button button--primary" type="button" @click="toggleNoteStatus(note)">{{ note.is_active ? 'Деактивировать' : 'Активировать' }}</button></div></article></div>
      </section>
      <section v-else-if="notesStore.activeTab === 'upcoming'" class="notes-view" :class="{ 'trash-view--loading': notesStore.isLoading }"><div v-for="group in [{ title: 'Сегодня', notes: upcomingGroups.today }, { title: 'На этой неделе', notes: upcomingGroups.week }, { title: 'Прошедшие', notes: upcomingGroups.overdue }]" :key="group.title" class="notes-group"><h2>{{ group.title }}</h2><div v-if="!group.notes.length" class="notes-empty">Нет заметок</div><div v-else class="trash-grid"><article v-for="note in group.notes" :key="note.id" class="trash-card"><div class="trash-card__body"><h2>{{ note.title }}</h2><p>{{ note.text || 'Без текста' }}</p><time :datetime="note.target_datetime">{{ formatUserDate(note.target_datetime, userSettingsStore.timezone) }}</time></div><div class="trash-card__actions"><button class="button button--quiet" type="button" @click="openEdit(note)">Изменить</button><button class="button button--primary" type="button" @click="toggleNoteStatus(note)">Завершить</button></div></article></div></div></section>
      <section v-else-if="notesStore.activeTab === 'completed'" class="trash-view" :class="{ 'trash-view--loading': notesStore.isLoading }"><div v-if="!notesStore.filteredNotes.length && !notesStore.isLoading" class="trash-empty">Выполненных заметок нет</div><div v-else class="trash-grid"><article v-for="note in notesStore.filteredNotes" :key="note.id" class="trash-card"><div class="trash-card__body"><h2>{{ note.title }}</h2><p>{{ note.text || 'Без текста' }}</p><time :datetime="note.target_datetime || note.updated_at">{{ formatUserDate(note.target_datetime || note.updated_at, userSettingsStore.timezone) }}</time></div><div class="trash-card__actions"><button class="button button--quiet" type="button" @click="openEdit(note)">Изменить</button><button class="button button--primary" type="button" @click="toggleNoteStatus(note)">Вернуть в активные</button></div></article></div></section>
      <section v-else class="trash-view" :class="{ 'trash-view--loading': notesStore.isLoading }">
        <div v-if="!notesStore.filteredNotes.length && !notesStore.isLoading" class="trash-empty">Корзина пуста</div>
        <div v-else class="trash-grid">
          <article v-for="note in notesStore.filteredNotes" :key="note.id" class="trash-card">
            <div class="trash-card__body">
              <h2>{{ note.title }}</h2>
              <p>{{ note.text || 'Без текста' }}</p>
              <div v-if="note.tags?.length" class="note-tags" style="display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 14px;" aria-label="Теги заметки"><span v-for="tag in note.tags" :key="tag.id" class="note-tag" :style="{ color: tag.color || '#3B82F6', border: `1px solid ${tag.color || '#3B82F6'}`, borderRadius: '999px', padding: '3px 8px', backgroundColor: `${tag.color || '#3B82F6'}18`, fontSize: '10px', fontWeight: '700' }">{{ tag.name }}</span></div>
              <time :datetime="note.target_datetime || note.deleted_at || note.updated_at">{{ formatUserDate(note.target_datetime || note.deleted_at || note.updated_at, userSettingsStore.timezone) }}</time>
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
