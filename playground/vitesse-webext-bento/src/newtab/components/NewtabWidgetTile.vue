<script setup lang="ts">
import type { WidgetItem } from '../composables/useNewtabLayout'

defineProps<{
  item: WidgetItem
}>()
</script>

<template>
  <div class="relative flex h-full flex-col justify-between">
    <div class="absolute inset-0 rounded-2xl bg-gradient-to-br opacity-75" :class="item.accent" />
    <div class="relative flex h-full flex-col justify-between">
      <div class="flex items-start justify-between gap-3">
        <div>
          <div class="text-base font-semibold tracking-tight text-white">
            {{ item.title }}
          </div>
          <div class="mt-1 text-xs uppercase tracking-[0.22em] text-white/60">
            Widget
          </div>
        </div>
        <div class="rounded-full border border-white/15 bg-black/10 px-2 py-1 text-[10px] text-white/70">
          {{ item.size }}
        </div>
      </div>

      <div class="rounded-2xl border border-white/15 bg-black/10 p-3 text-sm leading-6 text-white/80 shadow-inner whitespace-pre-line">
        {{ item.content }}
      </div>
    </div>
  </div>
</template>
