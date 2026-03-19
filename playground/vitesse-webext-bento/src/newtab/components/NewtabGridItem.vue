<script setup lang="ts">
import type { GridItem } from '../composables/useNewtabLayout'
import NewtabAppTile from './NewtabAppTile.vue'
import NewtabFolderTile from './NewtabFolderTile.vue'
import NewtabWidgetTile from './NewtabWidgetTile.vue'

const props = defineProps<{
  item: GridItem
}>()

const emit = defineEmits<{
  open: [item: GridItem]
}>()

function tileSpanClass() {
  if (props.item.type !== 'widget')
    return ''

  if (props.item.size === '2x2')
    return 'sm:col-span-2 sm:row-span-2'
  if (props.item.size === '2x1')
    return 'sm:col-span-2'
  return ''
}
</script>

<template>
  <button
    type="button"
    class="group relative flex min-h-[132px] flex-col overflow-hidden rounded-2xl border border-white/15 bg-white/10 p-4 text-left shadow-card backdrop-blur-md transition-all duration-300 hover:scale-105 hover:bg-white/15"
    :class="[
      tileSpanClass(),
    ]"
    @click="emit('open', item)"
  >
    <NewtabAppTile v-if="item.type === 'app'" :item="item" />
    <NewtabWidgetTile v-else-if="item.type === 'widget'" :item="item" />
    <NewtabFolderTile v-else :item="item" />
  </button>
</template>
