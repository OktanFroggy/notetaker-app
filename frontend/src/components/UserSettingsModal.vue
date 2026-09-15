<script setup>
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  firstRun: { type: Boolean, default: false },
  currentEmail: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'saved', 'switch-account'])
const form = reactive({ email: '', timezone: 'UTC' })
const isLoading = ref(false)
const isSaving = ref(false)
const error = ref('')
const timezones = [
  'UTC',
  'Europe/London',
  'Europe/Paris',
  'Europe/Moscow',
  'Asia/Dubai',
  'Asia/Bangkok',
  'Asia/Almaty',
  'Asia/Tokyo',
  'Australia/Sydney',
  'America/New_York',
  'America/Toronto',
  'America/Los_Angeles',
]
const timezoneOptions = computed(() => [...new Set([...timezones, form.timezone])])

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      'X-User-Email': options.email || props.currentEmail || form.email.trim(),
      ...(options.headers || {}),
    },
    ...options,
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}))
    throw new Error(detail.detail || 'Не удалось выполнить запрос')
  }
  return response.json()
}

async function loadSettings() {
  if (props.firstRun) {
    form.email = ''
    form.timezone = 'UTC'
    return
  }
  isLoading.value = true
  error.value = ''
  try {
    const settings = await request('/api/user/settings')
    form.email = settings.email
    form.timezone = settings.timezone
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    isLoading.value = false
  }
}

function close() { emit('update:modelValue', false) }

async function submit() {
  isSaving.value = true
  error.value = ''
  try {
    await request('/api/user/settings', {
      method: 'PUT',
      body: JSON.stringify({ email: form.email.trim(), timezone: form.timezone }),
    })
    emit('saved', form.email.trim())
    close()
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    isSaving.value = false
  }
}

watch(() => [props.modelValue, props.firstRun], ([isOpen]) => {
  if (isOpen) loadSettings()
}, { immediate: true })
</script>

<template>
  <div v-if="modelValue" class="modal-backdrop" @click.self="close">
    <section class="modal settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-modal-title">
      <div class="modal-header">
        <div><p class="eyebrow">Профиль</p><h2 id="settings-modal-title">{{ firstRun ? 'Введите ваш Email для входа' : 'Настройки профиля' }}</h2></div>
        <button class="close-button" type="button" aria-label="Закрыть" @click="close">×</button>
      </div>
      <div v-if="isLoading" class="settings-status">Загрузка настроек...</div>
      <form v-else @submit.prevent="submit">
        <div v-if="error" class="settings-error" role="alert">{{ error }}</div>
        <label class="field-label">Email пользователя<input v-model="form.email" type="email" required maxlength="255" autocomplete="email" /></label>
        <label v-if="!firstRun" class="field-label">Часовой пояс<select v-model="form.timezone" required><option v-for="timezone in timezoneOptions" :key="timezone" :value="timezone">{{ timezone }}</option></select></label>
        <div class="modal-actions"><button v-if="!firstRun" class="button button--quiet" type="button" @click="emit('switch-account')">Сменить аккаунт/Email</button><button v-if="!firstRun" class="button button--quiet" type="button" @click="close">Отмена</button><button class="button button--primary" type="submit" :disabled="isSaving">{{ isSaving ? 'Сохранение...' : 'Сохранить' }}</button></div>
      </form>
    </section>
  </div>
</template>