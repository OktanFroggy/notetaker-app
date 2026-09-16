<script setup>
import { reactive, watch } from 'vue'
import { useUserSettingsStore } from '../stores/userSettings'
import { dateTimeLocalToIso, toDateTimeLocal } from '../utils/dates'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  note: { type: Object, default: null },
  tags: { type: Array, default: () => [] },
  conflict: { type: Boolean, default: false },
})
const userSettingsStore = useUserSettingsStore()
const emit = defineEmits(['update:modelValue', 'save', 'delete', 'toggle-status', 'reload-current'])
const reminderOptions = [
  { offset: 10, label: 'За 10 минут' },
  { offset: 60, label: 'За 1 час' },
  { offset: 1440, label: 'За 1 день' },
]
const form = reactive({ title: '', text: '', target_datetime: '', repeat: 'none', repeat_until: '', tag_ids: [], reminderOffsets: [] })

watch(() => [props.note, userSettingsStore.timezone], ([note]) => {
  form.title = note?.title || ''
  form.text = note?.text || ''
  form.target_datetime = note?.target_datetime ? toDateTimeLocal(note.target_datetime, userSettingsStore.timezone) : ''
  form.repeat = note?.repeat || 'none'
  form.repeat_until = note?.repeat_until ? toDateTimeLocal(note.repeat_until, userSettingsStore.timezone) : ''
  form.tag_ids = note?.tags?.map((tag) => tag.id) || []
  form.reminderOffsets = note?.reminders?.map((reminder) => reminder.offset_minutes) || []
}, { immediate: true })

function close() { emit('update:modelValue', false) }
function submit() {
  const targetDatetime = form.target_datetime ? dateTimeLocalToIso(form.target_datetime, userSettingsStore.timezone) : null
  const reminders = targetDatetime ? form.reminderOffsets.map((offset) => ({
    offset_minutes: offset,
    remind_at: new Date(new Date(targetDatetime).getTime() - offset * 60 * 1000).toISOString(),
    is_sent: false,
  })) : []
  emit('save', { title: form.title.trim(), text: form.text.trim(), target_datetime: targetDatetime, repeat: form.repeat, repeat_until: form.repeat !== 'none' && form.repeat_until ? dateTimeLocalToIso(form.repeat_until, userSettingsStore.timezone) : null, is_active: props.note?.is_active ?? true, tag_ids: form.tag_ids, reminders })
}
</script>

<template>
  <div v-if="modelValue" class="modal-backdrop" @click.self="close">
    <section class="modal" role="dialog" aria-modal="true" aria-labelledby="note-modal-title">
      <div class="modal-header"><div><p class="eyebrow">{{ note ? 'Редактирование' : 'Новая запись' }}</p><h2 id="note-modal-title">{{ note ? 'Изменить заметку' : 'Запланировать мысль' }}</h2></div><button class="close-button" type="button" aria-label="Закрыть" @click="close">×</button></div>
      <form @submit.prevent="submit">
        <div v-if="conflict" class="conflict-warning" role="alert"><strong>Заметка была изменена в другом окне.</strong><span>Загрузите актуальную версию перед повторным сохранением.</span><button type="button" @click="emit('reload-current')">Загрузить актуальную версию</button></div>
        <label class="field-label">Заголовок<input v-model="form.title" required maxlength="255" placeholder="О чём нужно помнить?" /></label>
        <label class="field-label">Текст заметки<textarea v-model="form.text" rows="5" placeholder="Добавьте детали, контекст или следующий шаг..."></textarea></label>
        <div class="field-grid"><label class="field-label">Дата и время<input v-model="form.target_datetime" type="datetime-local" /></label><label class="field-label">Повторение<select v-model="form.repeat"><option value="none">Не повторять</option><option value="daily">Каждый день</option><option value="weekly">Каждую неделю</option><option value="monthly">Каждый месяц</option></select></label></div>
        <label v-if="form.repeat !== 'none'" class="field-label">Дата окончания повтора<input v-model="form.repeat_until" type="datetime-local" :min="form.target_datetime" required /><span class="field-hint">Повторение будет выполняться до этой даты</span></label>
        <fieldset class="reminder-picker"><legend>Напоминания</legend><label v-for="option in reminderOptions" :key="option.offset" class="tag-check"><input v-model="form.reminderOffsets" :value="option.offset" type="checkbox" :disabled="!form.target_datetime" />{{ option.label }}</label><span v-if="!form.target_datetime" class="field-hint">Сначала укажите дату и время</span></fieldset>
        <fieldset class="tag-picker"><legend>Теги</legend><label v-for="tag in tags" :key="tag.id" class="tag-check"><input v-model="form.tag_ids" :value="tag.id" type="checkbox" /><span class="tag-dot" :style="{ backgroundColor: tag.color || '#d97757' }"></span>{{ tag.name }}</label><span v-if="!tags.length" class="muted">Теги пока не созданы</span></fieldset>
        <div class="modal-actions"><button v-if="note" class="button button--quiet" type="button" @click="emit('toggle-status', note)">{{ note.is_active ? 'Завершить' : 'Вернуть в активные' }}</button><button v-if="note" class="button button--quiet" type="button" @click="emit('delete', note)">Удалить</button><button class="button button--quiet" type="button" @click="close">Отмена</button><button class="button button--primary" type="submit">{{ note ? 'Сохранить изменения' : 'Создать заметку' }}</button></div>
      </form>
    </section>
  </div>
</template>
