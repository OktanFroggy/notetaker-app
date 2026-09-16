<script setup>
import { ref } from 'vue'

const props = defineProps({
  tags: { type: Array, default: () => [] },
  selectedTagId: { type: Number, default: null },
  activeTab: { type: String, default: 'calendar' },
  isTrashView: { type: Boolean, default: false },
  noteCount: { type: Number, default: 0 },
})

const emit = defineEmits(['select-tag', 'select-calendar', 'select-list', 'select-completed', 'select-upcoming', 'new-note', 'open-trash', 'add-tag', 'update-tag', 'delete-tag'])
const tagName = ref('')
const tagColor = ref('#3B82F6')
const editingTagId = ref(null)
const showTagInput = ref(false)

function chooseTag(id) { emit('select-tag', id) }
function addTag() {
  if (tagName.value.trim()) {
    const payload = { name: tagName.value.trim(), color: tagColor.value }
    emit(editingTagId.value ? 'update-tag' : 'add-tag', editingTagId.value ? { id: editingTagId.value, ...payload } : payload)
    closeTagForm()
  }
}
function editTag(tag) { editingTagId.value = tag.id; tagName.value = tag.name; tagColor.value = tag.color || '#3B82F6'; showTagInput.value = true }
function closeTagForm() { tagName.value = ''; tagColor.value = '#3B82F6'; editingTagId.value = null; showTagInput.value = false }
function requestDeleteTag(tag) { emit('delete-tag', tag) }
</script>

<template>
  <aside class="sidebar">
    <div class="brand"><span class="brand-mark">N</span><span>notetaker</span></div>
    <button class="new-note-button" type="button" @click="emit('new-note')"><span>+</span> Новая заметка</button>

    <nav class="sidebar-nav" aria-label="Навигация">
      <button class="nav-item" :class="{ 'nav-item--active': activeTab === 'calendar' }" type="button" @click="emit('select-calendar')"><span class="nav-icon">◷</span> Календарь</button>
      <button class="nav-item" :class="{ 'nav-item--active': activeTab === 'list' }" type="button" @click="emit('select-list')"><span class="nav-icon">☷</span> Список</button>
      <button class="nav-item" :class="{ 'nav-item--active': activeTab === 'upcoming' }" type="button" @click="emit('select-upcoming')"><span class="nav-icon">⌁</span> Ближайшее</button>
      <button class="nav-item" :class="{ 'nav-item--active': activeTab === 'completed' }" type="button" @click="emit('select-completed')"><span class="nav-icon">✓</span> Выполненные</button>
      <button class="nav-item" :class="{ 'nav-item--active': isTrashView }" type="button" @click="emit('open-trash')"><span class="nav-icon">⌫</span> Корзина</button>
    </nav>

    <div class="sidebar-section">
      <div class="section-heading"><span>Теги</span><button class="icon-button" type="button" title="Добавить тег" @click="showTagInput = !showTagInput">+</button></div>
      <form v-if="showTagInput" class="tag-form" @submit.prevent="addTag"><input v-model="tagName" autofocus placeholder="Название тега" /><label class="tag-color-picker" title="Цвет тега"><input v-model="tagColor" type="color" /></label><button type="submit">{{ editingTagId ? 'Сохранить' : 'Добавить' }}</button><button class="tag-form-cancel" type="button" @click="closeTagForm">×</button></form>
      <button class="tag-item tag-item--all" :class="{ 'tag-item--selected': !selectedTagId }" type="button" @click="chooseTag(null)"><span class="tag-dot tag-dot--all">•</span> Все заметки <span class="tag-count">{{ noteCount }}</span></button>
      <div v-for="tag in tags" :key="tag.id" class="tag-row"><button class="tag-item" :class="{ 'tag-item--selected': selectedTagId === tag.id }" type="button" @click="chooseTag(tag.id)"><span class="tag-dot" :style="{ backgroundColor: tag.color || '#3B82F6' }"></span>{{ tag.name }}</button><button class="tag-edit" type="button" title="Изменить тег" @click="editTag(tag)">✎</button><button class="tag-delete" type="button" title="Удалить тег" @click="requestDeleteTag(tag)">×</button></div>
    </div>

    <div class="sidebar-footer">Сосредоточьтесь на важном.<br /><span>Ваше пространство для мыслей.</span></div>
  </aside>
</template>
