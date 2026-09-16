import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from './api'

export const useUserSettingsStore = defineStore('userSettings', () => {
  const email = ref('')
  const timezone = ref('UTC')

  async function load() {
    const settings = await api('/api/user/settings')
    email.value = settings.email
    timezone.value = settings.timezone || 'UTC'
    return settings
  }

  function setSettings(settings) {
    email.value = settings.email
    timezone.value = settings.timezone || 'UTC'
  }

  return { email, timezone, load, setSettings }
})
