<script setup lang="ts">
import { ArrowLeft, MapPin, Search, Users } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import TeamLabel from './TeamLabel.vue'
import type { SquadPlayer, TeamProfile } from '../types'

const props = defineProps<{ teamId: number }>()
const profile = ref<TeamProfile>()
const error = ref('')
const loading = ref(true)
const position = ref('all')
const search = ref('')
const positionGroups = [
  { id: 'Goalkeeper', name: '门将' },
  { id: 'Defence', name: '后卫' },
  { id: 'Midfield', name: '中场' },
  { id: 'Offence', name: '前锋' },
  { id: 'other', name: '位置未标注' },
]
const synced = computed(() => {
  const timestamp = profile.value?.meta.last_synced_at
  return timestamp ? new Date(timestamp).toLocaleString('zh-CN', { hour12: false }) : '—'
})
const season = computed(() => {
  const dates = profile.value?.season
  return dates ? `${dates.start_date.slice(0, 4)}/${dates.end_date.slice(2, 4)}` : ''
})
const groups = computed(() => {
  const players = profile.value?.roster?.players ?? []
  const byPosition = new Map<string, SquadPlayer[]>(positionGroups.map((group) => [group.id, []]))
  const query = search.value.trim().toLocaleLowerCase()
  for (const player of players) {
    if (query && !player.name.toLocaleLowerCase().includes(query)) continue
    const group = player.position && byPosition.has(player.position) ? player.position : 'other'
    byPosition.get(group)?.push(player)
  }
  return positionGroups.map((group) => ({ ...group, players: byPosition.get(group.id) ?? [] }))
    .filter((group) => group.players.length && (position.value === 'all' || group.id === position.value))
})

async function loadProfile() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch(`/api/v1/teams/${props.teamId}`, { signal: AbortSignal.timeout(10000) })
    if (response.status === 404) {
      error.value = '当前赛季没有这支球队。'
      return
    }
    if (!response.ok) throw new Error('Team request failed')
    profile.value = await response.json() as TeamProfile
  } catch {
    error.value = '暂时无法读取球队资料。'
  } finally {
    loading.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <a class="lab-back" href="#lab/teams"><ArrowLeft :size="17" /> 英超球队</a>
  <p v-if="loading" class="panel panel-state" role="status">正在读取球队阵容…</p>
  <div v-else-if="error" class="panel panel-state" role="status">
    {{ error }} <button class="text-button" type="button" @click="loadProfile">重试</button>
  </div>
  <template v-else-if="profile">
    <header class="team-profile panel">
      <div class="team-profile-main">
        <div class="lab-kicker">英格兰超级联赛 · {{ season }} 赛季</div>
        <h1><TeamLabel :team="profile.team" /></h1>
        <p class="profile-original">{{ profile.team.name }}</p>
      </div>
      <div v-if="profile.roster" class="profile-facts">
        <span><Users :size="17" /> {{ profile.roster.players.length }} 名球员</span>
        <span v-if="profile.roster.venue"><MapPin :size="17" /> {{ profile.roster.venue }}</span>
        <span v-if="profile.roster.coach">主教练 {{ profile.roster.coach }}</span>
      </div>
    </header>

    <section class="panel squad-panel" aria-labelledby="squad-heading">
      <header class="panel-header squad-header">
        <div>
          <div class="panel-title">
            <span class="section-icon"><Users :size="17" /></span>
            <h2 id="squad-heading">赛季球员名单</h2>
          </div>
          <p v-if="profile.roster" class="squad-meta">名单最近同步 {{ synced }}</p>
        </div>
        <div v-if="profile.roster" class="squad-controls">
          <label class="squad-search"><Search :size="15" />
            <input v-model="search" type="search" placeholder="搜索球员" aria-label="搜索球员" />
          </label>
          <select v-model="position" aria-label="按位置筛选">
            <option value="all">全部位置</option>
            <option v-for="group in positionGroups" :key="group.id" :value="group.id">{{ group.name }}</option>
          </select>
        </div>
      </header>
      <p v-if="!profile.roster" class="panel-state" role="status">暂无本赛季名单，请等待下一次数据同步。</p>
      <p v-else-if="!groups.length" class="panel-state" role="status">没有符合条件的球员。</p>
      <section v-for="group in groups" :key="group.id" class="roster-group" :aria-label="group.name">
        <h3>{{ group.name }} <small>{{ group.players.length }} 人</small></h3>
        <ul class="roster-players">
          <li v-for="player in group.players" :key="player.id">
            <strong>{{ player.name }}</strong>
            <span>{{ player.nationality || '国籍待补充' }}</span>
          </li>
        </ul>
      </section>
    </section>
  </template>
</template>
