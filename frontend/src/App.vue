<script setup lang="ts">
import {
  Activity, CalendarDays, CircleAlert, Clock3, LayoutDashboard, ListOrdered,
  RefreshCw, ScanLine, Target, Trophy,
} from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import FixtureList from './components/FixtureList.vue'
import LeagueStandings from './components/LeagueStandings.vue'
import { teamDisplayName } from './teamNames'
import { isComplete, type Dashboard } from './types'

const links = [
  { target: 'overview', label: '比赛中心', icon: LayoutDashboard },
  { target: 'standings', label: '积分榜', icon: ListOrdered },
  { target: 'fixtures', label: '赛程赛果', icon: CalendarDays },
]
const section = ref('overview')
const dashboard = ref<Dashboard>()
const loading = ref(false)
const error = ref('')
const syncFormatter = new Intl.DateTimeFormat('zh-CN', {
  month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
})

const seasonLabel = computed(() => {
  const season = dashboard.value?.season
  return season ? `${season.start_date.slice(0, 4)}/${season.end_date.slice(2, 4)}` : ''
})
const lastSynced = computed(() => dashboard.value
  ? syncFormatter.format(new Date(dashboard.value.meta.last_synced_at))
  : '')
const played = computed(() => dashboard.value?.matches.filter(isComplete) ?? [])
const averageGoals = computed(() => {
  const results = played.value.filter((match) => match.home_score !== null && match.away_score !== null)
  if (!results.length) return '—'
  const goals = results.reduce((sum, match) => sum + (match.home_score ?? 0) + (match.away_score ?? 0), 0)
  return (goals / results.length).toFixed(2)
})
const leader = computed(() => dashboard.value?.standings[0])

function readAnchor() {
  section.value = window.location.hash.slice(1) || 'overview'
}

async function loadDashboard() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/v1/competitions/PL', { signal: AbortSignal.timeout(10000) })
    if (response.status === 503) {
      error.value = '暂无缓存数据，请先在本地同步英超数据。'
      return
    }
    if (!response.ok) throw new Error('Dashboard request failed')
    dashboard.value = await response.json() as Dashboard
  } catch {
    error.value = dashboard.value
      ? '刷新失败，正在显示上次加载的数据。'
      : '暂时无法加载数据，请稍后重试。'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  readAnchor()
  window.addEventListener('hashchange', readAnchor)
  void loadDashboard().then(() => {
    if (section.value !== 'overview') document.getElementById(section.value)?.scrollIntoView()
  })
})
onUnmounted(() => window.removeEventListener('hashchange', readAnchor))
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar" aria-label="主导航">
      <a class="brand" href="#overview" aria-label="FootScope 比赛中心">
        <span class="brand-icon"><ScanLine :size="23" :stroke-width="2.2" /></span>
        <span>Foot<span class="brand-accent">Scope</span></span>
      </a>
      <nav class="nav-links">
        <a
          v-for="link in links"
          :key="link.target"
          :href="`#${link.target}`"
          class="nav-link"
          :class="{ active: section === link.target }"
          :aria-current="section === link.target ? 'location' : undefined"
        >
          <component :is="link.icon" :size="17" />
          <span>{{ link.label }}</span>
        </a>
      </nav>
      <div class="sidebar-bottom">
        <Activity :size="15" />
        <span>数据由 football-data.org 提供</span>
      </div>
    </aside>

    <main id="overview" class="workspace">
      <header class="topbar">
        <span class="breadcrumb"><span>比赛中心</span><span aria-hidden="true">/</span><strong>英超</strong></span>
        <div class="sync-tools">
          <span v-if="lastSynced" class="sync-time">
            <Clock3 :size="14" />
            <span>最近同步 {{ lastSynced }}</span>
          </span>
          <button type="button" class="icon-button refresh-button" title="重新读取缓存" aria-label="重新读取缓存" :disabled="loading" @click="loadDashboard">
            <RefreshCw :size="16" :class="{ spinning: loading }" />
          </button>
        </div>
      </header>

      <div class="workspace-content">
        <section class="hero" aria-labelledby="page-title">
          <div class="hero-content">
            <div class="hero-kicker"><span></span> PREMIER LEAGUE</div>
            <h1 id="page-title">英格兰超级联赛</h1>
            <div class="hero-meta">
              <span v-if="seasonLabel" class="season-pill">{{ seasonLabel }} 赛季</span>
              <span class="delay-pill"><span></span> 比分延迟</span>
            </div>
          </div>
        </section>

        <div v-if="error || dashboard?.meta.is_stale" class="notice" role="status">
          <CircleAlert :size="17" />
          <span>{{ error || '上次同步已超过 24 小时，积分榜和赛果可能有延迟。' }}</span>
        </div>
        <template v-if="dashboard">
          <div class="metrics" aria-label="赛季统计">
            <div class="metric">
              <span class="metric-icon"><CalendarDays :size="20" /></span>
              <div>
                <p>赛季进度</p>
                <div class="metric-value">{{ played.length }} <small>/ {{ dashboard.matches.length }} 场</small></div>
              </div>
            </div>
            <div class="metric">
              <span class="metric-icon goals-icon"><Target :size="20" /></span>
              <div>
                <p>场均进球</p>
                <div class="metric-value">{{ averageGoals }} <small>球</small></div>
              </div>
            </div>
            <div v-if="leader" class="metric">
              <span class="metric-icon leader-icon"><Trophy :size="19" /></span>
              <div class="leader-content">
                <p>榜首球队</p>
                <div class="metric-value leader-value" :title="leader.team.name">
                  <span>{{ teamDisplayName(leader.team) }}</span><small>{{ leader.points }} 分</small>
                </div>
              </div>
            </div>
          </div>
          <div class="dashboard-grid">
            <LeagueStandings :standings="dashboard.standings" />
            <FixtureList :matches="dashboard.matches" :current-matchday="dashboard.season.current_matchday" />
          </div>
        </template>
        <p v-else-if="loading" class="panel-state" role="status">正在读取英超数据…</p>

        <footer class="footer">
          <a href="https://www.football-data.org/" target="_blank" rel="noreferrer">
            Football data provided by the Football-Data.org API
          </a>
        </footer>
      </div>
    </main>
  </div>
</template>
