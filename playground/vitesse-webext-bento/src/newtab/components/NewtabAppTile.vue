<script setup lang="ts">
import type { AppItem } from '../composables/useNewtabLayout'

defineProps<{
  item: AppItem
}>()
</script>

<template>
  <div class="relative flex h-full flex-col items-center justify-center text-center">
    <div class="absolute inset-x-0 top-0 h-20 rounded-t-2xl bg-gradient-to-br opacity-80" :class="item.accent" />
    <div class="relative flex flex-col items-center">
      <div class="mb-3 flex h-16 w-16 items-center justify-center rounded-full border border-white/20 bg-white/80 text-2xl font-semibold text-slate-900 shadow-sm">
        {{ item.icon }}
      </div>
      <div class="text-sm font-medium text-white">
        {{ item.title }}
      </div>
      <div class="mt-1 text-xs text-white/65">
        {{ item.description }}
      </div>
    </div>
  </div>
</template>
