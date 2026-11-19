<script setup lang="ts">
import { ChevronRight, Users } from '@lucide/vue'
import { computed } from 'vue'
import SeasonMatches from './SeasonMatches.vue'
import TeamLabel from './TeamLabel.vue'
import type { Dashboard } from '../types'

const props = defineProps<{ dashboard?: Dashboard; showClubs: boolean; loading: boolean; error: string }>()
defineEmits<{ retry: [] }>()
const clubs = computed(() => props.dashboard?.standings ?? [])
</script>

<template>
  <header class="lab-heading">
    <h1>战术实验室</h1>
    <nav class="lab-tabs" aria-label="战术实验室">
      <a href="#lab" :aria-current="showClubs ? undefined : 'page'">本赛季英超</a>
      <a href="#lab/teams" :aria-current="showClubs ? 'page' : undefined">英超球队</a>
    </nav>
  </header>
  <section v-if="showClubs" class="panel" aria-labelledby="clubs-heading">
    <header class="panel-header">
      <div class="panel-title">
        <span class="section-icon"><Users :size="17" /></span>
        <h2 id="clubs-heading">英超球队阵容</h2>
      </div>
      <span v-if="clubs.length" class="subtle-label">{{ clubs.length }} 支球队</span>
    </header>
    <div v-if="clubs.length" class="club-directory">
      <a v-for="row in clubs" :key="row.team.id" :href="`#teams/${row.team.id}`" class="club-card">
        <TeamLabel :team="row.team" />
        <ChevronRight :size="14" aria-hidden="true" />
      </a>
    </div>
    <p v-else class="panel-state" role="status">{{ loading ? '正在读取球队…' : '暂无球队数据，请先同步英超赛季数据。' }}</p>
  </section>
  <SeasonMatches v-else-if="dashboard" :dashboard="dashboard" />
  <p v-else-if="loading" class="panel panel-state" role="status">正在读取英超赛程…</p>
  <div v-else-if="error" class="notice" role="status">
    {{ error }} <button type="button" class="text-button" @click="$emit('retry')">重试</button>
  </div>
</template>
