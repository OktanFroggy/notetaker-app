<script setup>
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: 'Подтвердите действие' },
  message: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Подтвердить' },
})

const emit = defineEmits(['update:modelValue', 'confirm'])

function close() { emit('update:modelValue', false) }
function confirm() { emit('confirm') }
</script>

<template>
  <div v-if="props.modelValue" class="modal-backdrop" @click.self="close">
    <section class="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="confirm-modal-title">
      <div class="confirm-modal__mark">!</div>
      <h2 id="confirm-modal-title">{{ title }}</h2>
      <p>{{ message }}</p>
      <div class="confirm-modal__actions">
        <button class="button button--quiet" type="button" @click="close">Отмена</button>
        <button class="button button--danger" type="button" @click="confirm">{{ confirmLabel }}</button>
      </div>
    </section>
  </div>
</template>
