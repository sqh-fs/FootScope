<script lang="ts">
const crests = import.meta.glob<string>('../assets/crests/*.png', {
  eager: true,
  import: 'default',
  query: '?url',
})
</script>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { teamDisplayName } from '../teamNames'
import type { Team } from '../types'

const props = defineProps<{ team: Team }>()
const crest = computed(() => crests[`../assets/crests/${props.team.id}.png`])
const failedCrest = ref<string>()
</script>

<template>
  <span class="team-label" :title="team.name">
    <img v-if="crest && crest !== failedCrest" class="team-crest" :src="crest" alt="" @error="failedCrest = crest" />
    <span v-else class="team-monogram" :class="`team-tone-${team.id % 6}`" aria-hidden="true">
      {{ team.code }}
    </span>
    <span class="team-name">{{ teamDisplayName(team) }}</span>
  </span>
</template>
