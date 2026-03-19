<script setup lang="ts">
const modelValue = defineModel<string>({ default: '' })
</script>

<template>
  <div class="mx-auto w-full max-w-3xl">
    <div class="rounded-[2rem] border border-white/20 bg-white/15 px-5 py-3 shadow-lg backdrop-blur-md transition-all duration-300 focus-within:scale-[1.01] focus-within:ring-2 focus-within:ring-white/40">
      <div class="flex items-center gap-3">
        <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/15 bg-black/10 text-sm text-white/70">
          ⌘K
        </div>
        <input
          v-model="modelValue"
          type="text"
          placeholder="搜索网页、应用、命令..."
          class="w-full bg-transparent text-base text-white placeholder:text-white/60 outline-none"
        >
      </div>
    </div>
  </div>
</template>
