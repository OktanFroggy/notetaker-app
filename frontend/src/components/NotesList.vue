<script setup>
import { reactive } from 'vue'

const props = defineProps({
  tags: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  notes: { type: Array, default: () => [] },
  initialSearch: { type: String, default: '' },
})
const emit = defineEmits(['apply', 'open'])
const filters = reactive({
  search: props.initialSearch,
  target_from: '',
  target_to: '',
  status: 'all',
  tag_ids: [],
  sort_by: 'updated_at_desc',
})

function apply() {
  emit('apply', { ...filters, tag_ids: [...filters.tag_ids] })
}
</script>

<template>
  <section class="notes-list-view" :class="{ 'trash-view--loading': loading }">
    <form class="list-filters" @submit.prevent="apply">
      <label class="field-label">Поиск<input v-model="filters.search" type="search" placeholder="Заголовок или текст" /></label>
      <label class="field-label">С даты<input v-model="filters.target_from" type="date" /></label>
      <label class="field-label">По дату<input v-model="filters.target_to" type="date" /></label>
      <label class="field-label">Статус<select v-model="filters.status"><option value="all">Все</option><option value="active">Активные</option><option value="inactive">Деактивированные</option></select></label>
      <label class="field-label">Сортировка<select v-model="filters.sort_by"><option value="updated_at_desc">По дате изменения</option><option value="event_date_asc">Дата заметки: сначала ранние</option><option value="event_date_desc">Дата заметки: сначала поздние</option></select></label>
      <fieldset class="tag-picker"><legend>Теги</legend><label v-for="tag in tags" :key="tag.id" class="tag-check"><input v-model="filters.tag_ids" :value="tag.id" type="checkbox" />{{ tag.name }}</label><span v-if="!tags.length" class="muted">Теги пока не созданы</span></fieldset>
      <button class="button button--primary" type="submit">Применить фильтры</button>
    </form>
    <div v-if="!notes.length && !loading" class="trash-empty">Заметки не найдены</div>
    <div v-else class="trash-grid">
      <article v-for="note in notes" :key="note.id" class="trash-card">
        <div class="trash-card__body"><h2>{{ note.title }}</h2><p>{{ note.text || 'Без текста' }}</p><div v-if="note.tags?.length" class="note-tags"><span v-for="tag in note.tags" :key="tag.id" class="note-tag">{{ tag.name }}</span></div><time :datetime="note.target_datetime || note.updated_at">{{ note.target_datetime || 'Без даты' }}</time></div>
        <div class="trash-card__actions"><button class="button button--quiet" type="button" @click="emit('open', note)">Изменить</button></div>
      </article>
    </div>
  </section>
</template>
