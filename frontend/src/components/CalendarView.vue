<script setup>
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import ruLocale from '@fullcalendar/core/locales/ru'

defineProps({
  events: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['date-click', 'event-click', 'event-drop'])

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
  eventClick: (info) => emit('event-click', info),
  eventDrop: (info) => emit('event-drop', info),
}
</script>

<template>
  <FullCalendar :options="{ ...calendarOptions, events }" />
</template>
