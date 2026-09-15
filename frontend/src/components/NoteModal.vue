<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  note: { type: Object, default: null },
  tags: { type: Array, default: () => [] },
  conflict: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'save', 'delete', 'toggle-status', 'reload-current'])
const form = reactive({ title: '', text: '', target_datetime: '', tag_ids: [], repeat: 'none' })

watch(() => props.note, (note) => {
  form.title = note?.title || ''
  form.text = note?.text || ''
  form.target_datetime = note?.target_datetime ? note.target_datetime.slice(0, 16) : ''
  form.tag_ids = note?.tags?.map((tag) => tag.id) || []
  form.repeat = 'none'
}, { immediate: true })

function close() { emit('update:modelValue', false) }
function submit() {
  emit('save', { title: form.title.trim(), text: form.text.trim(), target_datetime: form.target_datetime ? new Date(form.target_datetime).toISOString() : null, is_active: props.note?.is_active ?? true, tag_ids: form.tag_ids, reminders: [] })
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
        <fieldset class="tag-picker"><legend>Теги</legend><label v-for="tag in tags" :key="tag.id" class="tag-check"><input v-model="form.tag_ids" :value="tag.id" type="checkbox" /><span class="tag-dot" :style="{ backgroundColor: tag.color || '#d97757' }"></span>{{ tag.name }}</label><span v-if="!tags.length" class="muted">Теги пока не созданы</span></fieldset>
        <div class="modal-actions"><button v-if="note" class="button button--quiet" type="button" @click="emit('toggle-status', note)">{{ note.is_active ? 'Завершить' : 'Вернуть в активные' }}</button><button v-if="note" class="button button--quiet" type="button" @click="emit('delete', note)">Удалить</button><button class="button button--quiet" type="button" @click="close">Отмена</button><button class="button button--primary" type="submit">{{ note ? 'Сохранить изменения' : 'Создать заметку' }}</button></div>
      </form>
    </section>
  </div>
</template>
