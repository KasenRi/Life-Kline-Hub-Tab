<script setup lang="ts">
import Sortable from 'sortablejs'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { GridItem } from '../composables/useNewtabLayout'
import NewtabGridItem from './NewtabGridItem.vue'

const props = defineProps<{
  items: GridItem[]
}>()

const emit = defineEmits<{
  open: [item: GridItem]
  reorder: [oldIndex: number, newIndex: number]
}>()

const gridRef = ref<HTMLElement | null>(null)
let sortable: Sortable | null = null

function initSortable() {
  if (!gridRef.value)
    return

  sortable?.destroy()
  sortable = Sortable.create(gridRef.value, {
    animation: 220,
    easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
    ghostClass: 'tile-ghost',
    chosenClass: 'tile-chosen',
    dragClass: 'tile-drag',
    onEnd(event) {
      if (event.oldIndex == null || event.newIndex == null)
        return
      emit('reorder', event.oldIndex, event.newIndex)
    },
  })
}

watch(() => props.items.map(item => item.id).join('|'), async () => {
  await nextTick()
  initSortable()
})

onMounted(async () => {
  await nextTick()
  initSortable()
})

onBeforeUnmount(() => {
  sortable?.destroy()
  sortable = null
})
</script>

<template>
  <div
    ref="gridRef"
    class="grid auto-rows-[132px] grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6"
  >
    <NewtabGridItem
      v-for="item in items"
      :key="item.id"
      :item="item"
      @open="emit('open', $event)"
    />
  </div>
</template>
