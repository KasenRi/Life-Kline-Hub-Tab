<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { GridItem } from './composables/useNewtabLayout'
import { useNewtabLayout } from './composables/useNewtabLayout'
import NewtabBackgroundLayer from './components/NewtabBackgroundLayer.vue'
import NewtabGrid from './components/NewtabGrid.vue'
import NewtabPaginationDots from './components/NewtabPaginationDots.vue'
import NewtabSearchBar from './components/NewtabSearchBar.vue'
import wallpaperUrl from '~/assets/newtab-wallpaper.svg'

const clock = ref('')
const dateLabel = ref('')
const clockTimer = ref<number | null>(null)
const {
  activePage,
  activePageId,
  pages,
  reorderActivePage,
  searchTerm,
  setActivePage,
  visibleItems,
} = useNewtabLayout()

const totalTiles = computed(() => pages.value.reduce((count, page) => count + page.items.length, 0))

function updateClock() {
  const now = new Date()
  clock.value = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  dateLabel.value = now.toLocaleDateString([], {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  })
}

function openTile(tile: GridItem) {
  if (tile.type === 'app')
    window.open(tile.url, '_blank')
}

onMounted(() => {
  updateClock()
  clockTimer.value = window.setInterval(updateClock, 60_000)
})

onBeforeUnmount(() => {
  if (clockTimer.value != null)
    window.clearInterval(clockTimer.value)
})
</script>

<template>
  <div class="relative min-h-screen overflow-hidden bg-slate-950 text-white">
    <NewtabBackgroundLayer :wallpaper-url="wallpaperUrl" />

    <main class="relative z-10 flex min-h-screen flex-col px-5 py-6 sm:px-8 lg:px-12">
      <header class="mx-auto flex w-full max-w-7xl items-start justify-between gap-6 rounded-[2rem] border border-white/15 bg-white/10 p-5 shadow-glass backdrop-blur-xl">
        <div>
          <p class="text-xs uppercase tracking-[0.28em] text-white/60">
            Vitesse WebExt Bento
          </p>
          <h1 class="mt-3 text-3xl font-semibold tracking-tight sm:text-5xl">
            Sun-Panel inspired new tab shell
          </h1>
          <p class="mt-3 max-w-2xl text-sm leading-6 text-white/70 sm:text-base">
            iPadOS-like glass panels, Bento widgets, SortableJS drag sorting, and VueUse local-first state.
          </p>
        </div>

        <div class="rounded-[1.75rem] border border-white/15 bg-black/10 px-5 py-4 text-right shadow-card backdrop-blur-xl">
          <div class="text-xs uppercase tracking-[0.24em] text-white/55">
            Today
          </div>
          <div class="mt-2 text-3xl font-semibold tracking-tight">
            {{ clock }}
          </div>
          <div class="mt-1 text-sm text-white/65">
            {{ dateLabel }}
          </div>
          <div class="mt-4 inline-flex items-center rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs text-white/75">
            {{ totalTiles }} tiles
          </div>
        </div>
      </header>

      <section class="mx-auto mt-8 flex w-full max-w-7xl flex-1 flex-col gap-6">
        <div class="pt-6 sm:pt-10">
          <NewtabSearchBar v-model="searchTerm" />
        </div>

        <article class="flex-1 rounded-[2rem] border border-white/15 bg-white/10 p-5 shadow-glass backdrop-blur-xl">
          <div class="mb-5 flex items-end justify-between gap-4">
            <div>
              <h2 class="text-xl font-semibold tracking-tight text-white sm:text-2xl">
                {{ activePage?.title }}
              </h2>
              <p class="mt-1 text-sm text-white/65">
                Responsive grid with nested mock data ready for folders and future pagination drag.
              </p>
            </div>
            <div class="rounded-full border border-white/15 bg-black/10 px-3 py-1 text-xs uppercase tracking-[0.22em] text-white/55">
              SortableJS active
            </div>
          </div>

          <NewtabGrid
            v-if="activePage"
            :items="visibleItems"
            @open="openTile"
            @reorder="reorderActivePage"
          />
        </article>
      </section>

      <footer class="mt-8 pb-4">
        <NewtabPaginationDots
          :pages="pages"
          :active-page-id="activePageId"
          @select="setActivePage"
        />
      </footer>
    </main>
  </div>
</template>
