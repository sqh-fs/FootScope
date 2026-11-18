<script setup lang="ts">
import { CalendarDays, ChevronLeft, ChevronRight } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import TeamLabel from './TeamLabel.vue'
import { isComplete, type Match } from '../types'

const props = defineProps<{ matches: Match[]; currentMatchday: number | null }>()
const dayFormatter = new Intl.DateTimeFormat('zh-CN', {
  month: 'long', day: 'numeric', weekday: 'short',
})
const timeFormatter = new Intl.DateTimeFormat('zh-CN', {
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
})
const statusNames: Record<string, string> = {
  SCHEDULED: '待开赛',
  TIMED: '待开赛',
  IN_PLAY: '进行中',
  PAUSED: '中场休息',
  FINISHED: '已结束',
  AWARDED: '已判定',
  POSTPONED: '延期',
  SUSPENDED: '暂停',
  CANCELLED: '取消',
}

const rounds = computed(() => {
  const values = new Set(props.matches.map((match) => match.matchday))
  return [...values].sort((left, right) => (left ?? Infinity) - (right ?? Infinity))
})
const currentIndex = computed(() => {
  const fallback = props.matches.find((match) =>
    (match.status === 'TIMED' || match.status === 'SCHEDULED') &&
    Date.parse(match.kickoff_utc) >= Date.now(),
  )?.matchday
  const index = rounds.value.indexOf(props.currentMatchday ?? fallback ?? null)
  return index >= 0 ? index : 0
})
const selectedIndex = ref(0)
watch(currentIndex, (index) => { selectedIndex.value = index }, { immediate: true })
watch(rounds, (values) => {
  if (selectedIndex.value >= values.length) selectedIndex.value = currentIndex.value
})

const matchGroups = computed(() => {
  const groups = new Map<string, Match[]>()
  const selectedDay = rounds.value[selectedIndex.value]
  for (const match of props.matches) {
    if (match.matchday !== selectedDay) continue
    const date = dayFormatter.format(new Date(match.kickoff_utc))
    const entries = groups.get(date) ?? []
    entries.push(match)
    groups.set(date, entries)
  }
  return [...groups.entries()]
})

function result(match: Match) {
  if (match.home_score !== null && match.away_score !== null) {
    return `${match.home_score} – ${match.away_score}`
  }
  if (match.status === 'TIMED') {
    return timeFormatter.format(new Date(match.kickoff_utc))
  }
  return '—'
}
</script>

<template>
  <section id="fixtures" class="panel" aria-labelledby="fixtures-heading">
    <header class="panel-header">
      <div class="panel-title">
        <span class="section-icon"><CalendarDays :size="17" /></span>
        <h2 id="fixtures-heading">赛程与赛果</h2>
      </div>
      <button v-if="selectedIndex !== currentIndex" type="button" class="text-button" @click="selectedIndex = currentIndex">
        回到当前轮次
      </button>
    </header>
    <div class="round-control">
      <button type="button" class="icon-button" aria-label="上一轮" :disabled="selectedIndex <= 0" @click="selectedIndex--">
        <ChevronLeft :size="17" />
      </button>
      <select v-model="selectedIndex" aria-label="选择比赛轮次">
        <option v-for="(round, index) in rounds" :key="round ?? 'pending'" :value="index">
          {{ round === null ? '待定轮次' : `第 ${round} 轮` }}
        </option>
      </select>
      <button type="button" class="icon-button" aria-label="下一轮" :disabled="selectedIndex >= rounds.length - 1" @click="selectedIndex++">
        <ChevronRight :size="17" />
      </button>
    </div>
    <div v-if="matchGroups.length" class="fixture-groups" aria-live="polite">
      <div v-for="[date, matchesOnDate] in matchGroups" :key="date" class="fixture-group">
        <h3>{{ date }}</h3>
        <ul class="fixture-list">
          <li v-for="match in matchesOnDate" :key="match.id" class="fixture-row">
            <span class="fixture-home"><TeamLabel :team="match.home_team" /></span>
            <span class="fixture-center">
              <span class="fixture-result" :class="{ 'finished-result': isComplete(match) }">{{ result(match) }}</span>
              <span class="fixture-status" :class="{ 'in-play': match.status === 'IN_PLAY' }">{{ statusNames[match.status] ?? '状态待定' }}</span>
            </span>
            <span class="fixture-away"><TeamLabel :team="match.away_team" /></span>
          </li>
        </ul>
      </div>
    </div>
    <p v-else class="panel-state">本轮暂无比赛。</p>
  </section>
</template>
