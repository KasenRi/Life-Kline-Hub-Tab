<script setup lang="ts">
import type { GridPage } from '../composables/useNewtabLayout'

defineProps<{
  pages: GridPage[]
  activePageId: string
}>()

const emit = defineEmits<{
  select: [pageId: string]
}>()
</script>

<template>
  <div class="flex items-center justify-center">
    <div class="inline-flex items-center gap-3 rounded-full border border-white/15 bg-white/10 px-4 py-3 shadow-card backdrop-blur-md">
      <button
        v-for="page in pages"
        :key="page.pageId"
        type="button"
        class="group flex items-center gap-2"
        @click="emit('select', page.pageId)"
      >
        <span
          class="h-2.5 rounded-full transition-all duration-300"
          :class="page.pageId === activePageId ? 'w-8 bg-white' : 'w-2.5 bg-white/40 group-hover:bg-white/60'"
        />
        <span
          class="hidden text-xs tracking-[0.18em] text-white/65 sm:inline"
          :class="page.pageId === activePageId ? 'text-white' : ''"
        >
          {{ page.title }}
        </span>
      </button>
    </div>
  </div>
</template>
