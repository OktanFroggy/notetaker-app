import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useTagsStore = defineStore('tags', () => {
  const tags = ref([])
  const isLoading = ref(false)
  const error = ref('')

  async function loadTags() {
    isLoading.value = true
    try {
      const response = await fetch('/api/tags')
      if (!response.ok) throw new Error('Не удалось загрузить теги')
      tags.value = await response.json()
    } catch (requestError) {
      error.value = requestError.message
    } finally {
      isLoading.value = false
    }
  }

  async function createTag(payload) {
    const response = await fetch('/api/tags', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) throw new Error('Не удалось создать тег')
    const tag = await response.json()
    tags.value.push(tag)
    tags.value.sort((left, right) => left.name.localeCompare(right.name))
    return tag
  }

  async function deleteTag(id) {
    const response = await fetch(`/api/tags/${id}`, { method: 'DELETE' })
    if (!response.ok) throw new Error('Не удалось удалить тег')
    tags.value = tags.value.filter((tag) => tag.id !== id)
  }

  return { tags, isLoading, error, loadTags, createTag, deleteTag }
})
