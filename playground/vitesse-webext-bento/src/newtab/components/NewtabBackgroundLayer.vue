<script setup lang="ts">
defineProps<{
  wallpaperUrl: string
}>()
</script>

<template>
  <div
    class="absolute inset-0 bg-cover bg-center"
    :style="{ backgroundImage: `url(${wallpaperUrl})` }"
  />
  <div class="absolute inset-0 bg-gradient-to-b from-slate-950/35 via-slate-900/25 to-slate-950/45" />
  <div class="absolute inset-0 bg-white/5 backdrop-blur-xl" />
  <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.22),transparent_32%),radial-gradient(circle_at_bottom_right,rgba(255,255,255,0.16),transparent_28%)]" />
</template>
