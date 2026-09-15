<script setup>
import { ref } from 'vue'

const props = defineProps({
  tags: { type: Array, default: () => [] },
  selectedTagId: { type: Number, default: null },
  showCompleted: { type: Boolean, default: true },
  isTrashView: { type: Boolean, default: false },
  noteCount: { type: Number, default: 0 },
})

const emit = defineEmits(['select-tag', 'select-calendar', 'toggle-completed', 'new-note', 'open-trash', 'add-tag'])
const tagName = ref('')
const showTagInput = ref(false)

function chooseTag(id) { emit('select-tag', id) }
function addTag() {
  if (tagName.value.trim()) {
    emit('add-tag', { name: tagName.value.trim(), color: '#d97757' })
    tagName.value = ''
    showTagInput.value = false
  }
}
</script>

<template>
  <aside class="sidebar">
    <div class="brand"><span class="brand-mark">N</span><span>notetaker</span></div>
    <button class="new-note-button" type="button" @click="emit('new-note')"><span>+</span> Новая заметка</button>

    <nav class="sidebar-nav" aria-label="Навигация">
      <button class="nav-item" :class="{ 'nav-item--active': !isTrashView }" type="button" @click="emit('select-calendar')"><span class="nav-icon">◷</span> Календарь</button>
      <button class="nav-item" :class="{ 'nav-item--active': isTrashView }" type="button" @click="emit('open-trash')"><span class="nav-icon">⌫</span> Корзина</button>
    </nav>

    <div class="sidebar-section">
      <div class="section-heading"><span>Теги</span><button class="icon-button" type="button" title="Добавить тег" @click="showTagInput = !showTagInput">+</button></div>
      <form v-if="showTagInput" class="tag-form" @submit.prevent="addTag"><input v-model="tagName" autofocus placeholder="Название тега" /><button type="submit">Добавить</button></form>
      <button class="tag-item tag-item--all" :class="{ 'tag-item--selected': !selectedTagId }" type="button" @click="chooseTag(null)"><span class="tag-dot tag-dot--all">•</span> Все заметки <span class="tag-count">{{ noteCount }}</span></button>
      <button v-for="tag in tags" :key="tag.id" class="tag-item" :class="{ 'tag-item--selected': selectedTagId === tag.id }" type="button" @click="chooseTag(tag.id)"><span class="tag-dot" :style="{ backgroundColor: tag.color || '#d97757' }"></span>{{ tag.name }}</button>
    </div>

    <label class="sidebar-toggle"><input :checked="showCompleted" type="checkbox" @change="emit('toggle-completed', $event.target.checked)" /><span class="toggle-track"></span><span>Показывать выполненные</span></label>
    <div class="sidebar-footer">Сосредоточьтесь на важном.<br /><span>Ваше пространство для мыслей.</span></div>
  </aside>
</template>
