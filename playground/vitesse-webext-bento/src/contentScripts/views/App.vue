<script setup lang="ts">
import { useToggle } from '@vueuse/core'

const [show, toggle] = useToggle(false)
</script>

<template>
  <div class="fixed bottom-0 right-0 z-[100] m-5 flex items-end font-sans leading-none select-none">
    <div
      v-show="show"
      class="my-auto mr-2 h-min w-max rounded-lg bg-white px-4 py-2 text-gray-800 shadow transition-opacity duration-300"
      :class="show ? 'opacity-100' : 'opacity-0'"
    >
      <h1 class="text-lg">
        Vitesse WebExt
      </h1>
      <SharedSubtitle />
    </div>
    <button
      class="flex h-10 w-10 cursor-pointer rounded-full border-none bg-teal-600 shadow transition hover:bg-teal-700"
      @click="toggle()"
    >
      <pixelarticons-power class="block m-auto text-white text-lg" />
    </button>
  </div>
</template>
