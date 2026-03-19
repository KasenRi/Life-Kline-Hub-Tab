<script setup lang="ts">
import type { FolderItem } from '../composables/useNewtabLayout'

const props = defineProps<{
  item: FolderItem
}>()

function previewChildren() {
  return props.item.children.slice(0, 4)
}
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
          <div class="mt-1 text-xs text-white/65">
            {{ item.children.length }} items
          </div>
        </div>
        <div class="rounded-full border border-white/15 bg-black/10 px-2 py-1 text-[10px] uppercase tracking-[0.22em] text-white/70">
          Folder
        </div>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <div
          v-for="child in previewChildren()"
          :key="child.id"
          class="flex h-12 items-center justify-center rounded-2xl border border-white/15 bg-white/75 text-sm font-semibold text-slate-900 shadow-sm"
        >
          {{ child.icon }}
        </div>
      </div>
    </div>
  </div>
</template>
