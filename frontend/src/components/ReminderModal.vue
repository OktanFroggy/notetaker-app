<script setup>
import { useUserSettingsStore } from '../stores/userSettings'
import { formatUserDate } from '../utils/dates'
defineProps({
  modelValue: { type: Boolean, default: false },
  reminder: { type: Object, default: null },
})

const emit = defineEmits(['close'])
const userSettingsStore = useUserSettingsStore()

function close() { emit('close') }
</script>

<template>
  <div v-if="modelValue && reminder" class="modal-backdrop reminder-backdrop" @click.self="close">
    <section class="reminder-modal" role="alertdialog" aria-modal="true" aria-labelledby="reminder-modal-title">
      <div class="reminder-modal__icon" aria-hidden="true">⏰</div>
      <p class="eyebrow">Напоминание</p>
      <h2 id="reminder-modal-title">⏰ Напоминание о заметке</h2>
      <h3>{{ reminder.note.title }}</h3>
      <p class="reminder-modal__text">{{ reminder.note.content || reminder.note.text || 'Без описания' }}</p>
      <time class="reminder-modal__time" :datetime="reminder.note.event_date || reminder.note.target_datetime">
        {{ formatUserDate(reminder.note.event_date || reminder.note.target_datetime, userSettingsStore.timezone) }}
      </time>
      <div class="reminder-modal__actions">
        <button class="button button--primary" type="button" @click="close">Понятно</button>
      </div>
    </section>
  </div>
</template>