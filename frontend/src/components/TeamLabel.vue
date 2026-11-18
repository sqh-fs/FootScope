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

const props = defineProps<{ team: Team; linked?: boolean }>()
const crest = computed(() => crests[`../assets/crests/${props.team.id}.png`])
const failedCrest = ref<string>()
</script>

<template>
  <component
    :is="linked ? 'a' : 'span'"
    :href="linked ? `#teams/${team.id}` : undefined"
    class="team-label"
    :class="{ 'team-link': linked }"
    :title="team.name"
  >
    <img v-if="crest && crest !== failedCrest" class="team-crest" :src="crest" alt="" @error="failedCrest = crest" />
    <span v-else class="team-monogram" :class="`team-tone-${team.id % 6}`" aria-hidden="true">
      {{ team.code }}
    </span>
    <span class="team-name">{{ teamDisplayName(team) }}</span>
  </component>
</template>
