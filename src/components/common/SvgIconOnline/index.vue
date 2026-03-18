<script setup lang='ts'>
import { computed, useAttrs } from 'vue'
import { Icon } from '@iconify/vue'
import SvgIcon from '../SvgIcon/index.vue'

interface Props {
  icon?: string
}

const props = defineProps<Props>()

const attrs = useAttrs()
const fallbackIcons: Record<string, string> = {
  'subway:add': 'typcn-plus',
  'material-symbols:ad-group-outline': 'material-symbols-ad-group-outline-rounded',
}

const bindAttrs = computed<{ class: string; style: string }>(() => ({
  class: (attrs.class as string) || '',
  style: (attrs.style as string) || '',
}))

const fallbackIcon = computed(() => {
  if (!props.icon)
    return ''

  return fallbackIcons[props.icon] || ''
})
</script>

<template>
  <SvgIcon v-if="fallbackIcon" :icon="fallbackIcon" v-bind="bindAttrs" />
  <Icon v-else :icon="icon ?? ''" v-bind="bindAttrs" />
</template>
