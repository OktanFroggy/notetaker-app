import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from './api'

export const useTagsStore = defineStore('tags', () => {
  const tags = ref([])
  const isLoading = ref(false)
  const error = ref('')

  async function loadTags() {
    isLoading.value = true
    try {
      tags.value = await api('/api/tags')
    } catch (requestError) {
      error.value = requestError.message
    } finally {
      isLoading.value = false
    }
  }

  async function createTag(payload) {
    const tag = await api('/api/tags', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    tags.value.push(tag)
    tags.value.sort((left, right) => left.name.localeCompare(right.name))
    return tag
  }

  async function updateTag(id, payload) {
    const updatedTag = await api(`/api/tags/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
    const index = tags.value.findIndex((tag) => tag.id === id)
    if (index !== -1) tags.value[index] = updatedTag
    tags.value.sort((left, right) => left.name.localeCompare(right.name))
    return updatedTag
  }

  async function deleteTag(id) {
    await api(`/api/tags/${id}`, { method: 'DELETE' })
    tags.value = tags.value.filter((tag) => tag.id !== id)
    return id
  }

  return { tags, isLoading, error, loadTags, createTag, updateTag, deleteTag }
})
