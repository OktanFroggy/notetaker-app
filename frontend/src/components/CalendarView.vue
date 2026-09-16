<script setup>
import { computed } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import ruLocale from '@fullcalendar/core/locales/ru'
import { resolveMasterNoteId } from '../stores/notes'
import { useUserSettingsStore } from '../stores/userSettings'

defineProps({
  events: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['date-click', 'event-click', 'event-drop'])
const userSettingsStore = useUserSettingsStore()

function normalizeEventNote(info) {
  const note = info.event.extendedProps.note
  return { ...note, id: resolveMasterNoteId(note), occurrence_id: String(info.event.id) }
}

const calendarOptions = computed(() => ({
  initialView: 'dayGridMonth',
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  locales: [ruLocale],
  locale: 'ru',
  timeZone: userSettingsStore.timezone,
  editable: true,
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,timeGridDay',
  },
  dayMaxEvents: 3,
  fixedWeekCount: false,
  dateClick: (info) => emit('date-click', info),
  eventClick: (info) => emit('event-click', { info, note: normalizeEventNote(info) }),
  eventDrop: (info) => emit('event-drop', { info, note: normalizeEventNote(info) }),
}))
</script>

<template>
  <FullCalendar :options="{ ...calendarOptions, events }" />
</template>
