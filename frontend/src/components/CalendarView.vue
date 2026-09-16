<script setup>
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import ruLocale from '@fullcalendar/core/locales/ru'
import { resolveMasterNoteId } from '../stores/notes'

defineProps({
  events: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['date-click', 'event-click', 'event-drop'])

function normalizeEventNote(info) {
  const note = info.event.extendedProps.note
  return { ...note, id: resolveMasterNoteId(note) }
}

const calendarOptions = {
  initialView: 'dayGridMonth',
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  locales: [ruLocale],
  locale: 'ru',
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
}
</script>

<template>
  <FullCalendar :options="{ ...calendarOptions, events }" />
</template>
